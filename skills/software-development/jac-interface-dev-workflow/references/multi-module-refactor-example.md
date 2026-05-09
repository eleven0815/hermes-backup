# 多模块重构实战：移动 InterfaceLogService 与 InterfaceLogAspect

## 背景

用户要求将 `InterfaceLogService` 从 `api` 模块移到 `service` 模块。这是一个典型的 Java Maven 多模块重构场景，需要谨惬处理循环依赖。

## 模块现状

```
api          ← 无依赖，纯 DTO/接口定义
framework    ← api（AOP 切面、通用注解、框架级组件）
service      ← framework + api（ServiceImpl、repository 接口）
```

## 问题识别

1. `InterfaceLogService` 在 `api` 模块中被 `framework` 的 `InterfaceLogAspect` 和 `service` 的 `InterfaceLogInnerService` 同时引用。
2. 若只移动接口到 `service`，`framework` 的 `InterfaceLogAspect` 就会找不到类，必须让 `framework` 依赖 `service`。
3. 但 `service` 已经依赖 `framework`，这就形成了**循环依赖**：`service -> framework -> service`。

## 解决方案：切面下沉

将 `InterfaceLogAspect` 一并从 `framework` 下沉到 `service` 模块：

```bash
# 创建目标目录
mkdir -p dev-c-oem-isscp-common-service/src/main/java/com/yonyou/oem/common/aop

# 移动接口
mv dev-c-oem-isscp-common-api/.../api/service/InterfaceLogService.java \
   dev-c-oem-isscp-common-service/.../api/service/InterfaceLogService.java

# 移动切面
mv dev-c-oem-isscp-common-framework/.../aop/InterfaceLogAspect.java \
   dev-c-oem-isscp-common-service/.../aop/InterfaceLogAspect.java
```

## 编译验证

```bash
cd c-oem-isscp-common/c-oem-isscp-common-be
mvn clean compile -pl dev-c-oem-isscp-common-service -am -DskipTests
```

## 缓存陷阱：本地 Maven 仓库过期 jar

移动后编译可能报错：

```
无法将接口 com.yonyou.oem.common.api.service.InterfaceLogService 中的方法 saveLog 应用到给定类型;
  需要: SaveInterfaceReq,Object,Throwable,long,boolean
  找到:    SaveInterfaceReq,Object,Throwable,long
```

**原因**：本地 Maven 仓库中的 `c-oem-isscp-common-api` jar 是旧版本（包含 5 参数的 `saveLog` 方法），与当前源码不匹配。

**解决**：

```bash
# 删除过期缓存
rm ~/Desktop/JAC/开发/maven/repository/com/yonyou/ucf/c-oem-isscp-common-api/ddm-3.0-SNAPSHOT/c-oem-isscp-common-api-ddm-3.0-SNAPSHOT.jar

# 重新安装 api 模块
mvn clean install -pl dev-c-oem-isscp-common-api -am -DskipTests

# 全量编译
mvn clean install -DskipTests
```

## 关键教训

1. 移动代码前，先检查所有引用方的模块位置，特别关注 `framework` 是否引用了被移动的类。
2. 移动完成后必须运行 `mvn clean compile -DskipTests` 验证，最好是 `mvn clean install -DskipTests` 全量构建。
3. 遇到"方法签名不匹配"、"参数列表长度不同"等奇怪编译时，首先怀疑本地 Maven 仓库缓存过期。
4. 在 JAC 项目中，本地仓库路径通常是 `~/Desktop/JAC/开发/maven/repository/`，而非默认的 `~/.m2/repository/` 。
