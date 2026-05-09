# InterfaceAcceptLog 骨架生成与调整实例

## 背景
`ti_interface_accept_log`是调入日志表，与已有的 `ti_interface_send_log` 结构对称。本文档记录使用 `bip-generator` 生成该表骨架后的具体调整步骤，作为日志/配置类表生成的参考。

## 生成命令

```bash
/usr/bin/expect <<'EOF'
set timeout 30
spawn java -jar bip-generator-1.0-SNAPSHOT-jar-with-dependencies.jar
expect "输入项目名称"
send "common\r"
expect "请输入文件输出目录"
send "/tmp/bip-gen-accept-log\r"
expect "输入表名"
send "ti_interface_accept_log\r"
expect eof
EOF
```

## 必须手动调整的项

### 1. PO `YMSEntity` 注解
generator 生成：`name = "oem.common.interfaceacceptlog"`, `domain = "oem"`

应修正为与前端 VM 保持一致：
```java
@YMSEntity(name = "commonapiconfig.commonapiconfig.interfaceAcceptLog", domain = "c-oem-isscp-common")
```

### 2. 布尔类型不一致
generator 生成 `private Short interfaceSwitch;`

项目中 `InterfaceSendLog` / `SaveInterfaceReq` 均使用 `Boolean`，应修改 PO 和 DTO：
```java
private Boolean interfaceSwitch;
```

### 3. 删除 `setVerifyState`
generator 在 `RepositoryImpl.save()` 和 `saveBatch()` 中生成：
```java
po.setVerifyState((short) 0);
```

日志表 PO 无此字段，直接删除该行。

### 4. 补充避免避漏的字段
generator 未产出 `pathParam`，但 `InterfaceSendLog` 和 `SaveInterfaceReq` 均存在。在 PO 和 DTO 中手动添加：
```java
private String pathParam;
// getter + setter
```

### 5. RepositoryImpl 事务注解
日志保存必须独立事务，`saveLog` 方法添加：
```java
@Override
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void saveLog(SaveInterfaceReq interfaceReq) { ... }
```

### 6. 方法签名与现有模式对齐
参考 `InterfaceSendLogRepository` / `InterfaceSendLogRepositoryImpl`，确保方法签名一致：
- `saveLog(SaveInterfaceReq interfaceReq)` → void
- `updateDto(InterfaceAcceptLogDTO setDTO)` → void

### 7. Service 层补充 `saveLog`
```java
@Override
public void saveLog(SaveInterfaceReq interfaceReq) {
    repository.saveLog(interfaceReq);
}
```

### 8. Controller import 补充
generator 生成的 Controller 缺少 `SuperController` import：
```java
import com.yonyou.oem.common.framework.base.SuperController;
```

## 文件放置路径

| 文件 | 目标路径 |
|------|--------|
| InterfaceAcceptLog.java | `dev-c-oem-isscp-common-infrastructure/.../po/InterfaceAcceptLog.java` |
| InterfaceAcceptLogDTO.java | `dev-c-oem-isscp-common-api/.../dto/InterfaceAcceptLogDTO.java` |
| InterfaceAcceptLogConverter.java | `dev-c-oem-isscp-common-infrastructure/.../converter/InterfaceAcceptLogConverter.java` |
| InterfaceAcceptLogRepository.java | `dev-c-oem-isscp-common-service/.../repository/InterfaceAcceptLogRepository.java` |
| InterfaceAcceptLogRepositoryImpl.java | `dev-c-oem-isscp-common-infrastructure/.../repository/InterfaceAcceptLogRepositoryImpl.java` |
| InterfaceAcceptLogService.java | `dev-c-oem-isscp-common-service/.../service/InterfaceAcceptLogService.java` |
| InterfaceAcceptLogServiceImpl.java | `dev-c-oem-isscp-common-service/.../impl/InterfaceAcceptLogServiceImpl.java` |
| InterfaceAcceptLogController.java | `dev-c-oem-isscp-common-app/.../controller/InterfaceAcceptLogController.java` |

## 编译验证

```bash
cd c-oem-isscp-common/c-oem-isscp-common-be
mvn clean compile -DskipTests
```

特别关注 `infrastructure` 模块的 MapStruct 报错（如 `No implementation was created`）。
