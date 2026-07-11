---
name: jac-interface-dev-workflow
description: "JAC DMS项目SAP/WMS接口开发流程规范（YMS @RemoteCall RPC + IYmsJdbcApi DO模式 + bip-generator代码生成器）"
triggers:
  - "JAC接口开发"
  - "SAP接口"
  - "WMS接口"
  - "@RemoteCall"
  - "IYmsJdbcApi"
  - "bip-generator"
  - "调出接口"
  - "调入接口"
  - "接口规范"
---

# JAC DMS SAP/WMS接口开发流程

## 核心认知

- **透传架构**：DMS不做业务处理，只转发+记录日志。业务逻辑下沉到业务模块。
- **模块间调用**：使用 **YMS `@RemoteCall` RPC**（`com.yonyou.cloud.middleware.rpc.RemoteCall`），不是 OpenFeign/RestTemplate。
- **代码生成优先**：接口骨架代码（PO/Repository/Service/Controller）**优先由 `bip-generator` 生成**，非手写。手写易遗漏审计字段、破坏依赖关系、命名不规范。

## 踩坑清单（硬性规则）

| 问题 | 后果 | 正确做法 |
|------|------|---------|
| `service` 依赖 `infrastructure` | Maven 循环依赖 | `service` 绝不能依赖 `infrastructure`。repository 接口在 `service`，实现在 `infrastructure` |
| **移动代码到 framework 造成循环依赖** | framework 编译失败（找不到 service 中的类） | 将被引用的 repository/service 接口提取到 `api` 模块，`framework` 只引用 `api` 中的接口，由 `service` 模块实现。移动完成后 **必须全量编译** `mvn clean compile -DskipTests` 验证。 |
| **从 api 移动接口/类到 service 造成循环依赖** | `framework` 编译失败（找不到 service 中的类），或形成 `service -> framework -> service` 循环 | `framework` 中的 AOP 切面、通用组件若引用了被移动的接口，必须将切面/组件一并下沉到 `service`，或将接口保留在 `api`。移动完成后 **必须全量编译** `mvn clean compile -DskipTests` 验证。 |
| **移动代码后缺少 import 更新** | 编译失败（旧引用方还指向老路径） | 移动后搜索全工程所有引用该类的 import，统一更新为新路径。特别检查 aspect 中的注入类型是否仍为实现类。 |
| **Maven 本地仓库缓存过期 jar** | 编译错误（方法签名不匹配、参数列表长度不同、找不到符号），即使源码已修改 | 删除自定义 local repo（如 `~/开发/maven/repository/`）或 `~/.m2/repository/` 中对应模块的缓存 jar，重新 `mvn clean install -pl <模块> -am -DskipTests` |
| `@Transactional` 放接口上 | AOP 不生效 | 放 **repository 实现类** 的**具体方法**上 |
| 同类内 `@Transactional` 互相调用 | 事务不独立 | 提取到**独立 Spring Bean** |
| 手写 PO 遗漏 SuperDO 字段 | 数据不完整 | 用 `bip-generator` 生成，生成后确认 `id` 为 `String`、实现 `ILogicDelete` |
| 接口编码不统一 | 日志/配置混乱 | 统一格式 `SAP_{接口编码}` 或 `WMS_{接口编码}`，如 `SAP_SD016`、`WMS_ASNCREATE` |
| 日志切面无 SpEL 解析 | `interface_no` 记录字面量 `#interfaceCode` | `InterfaceLogAspect` 必须支持 SpEL |
| 接口数据和日志无独立事务 | 主业务异常导致数据丢失 | 使用 `REQUIRES_NEW` |
| **bip-generator pipe输入失败** | 表名和输出目录不被识别 | 用 `/usr/bin/expect` 模拟交互式终端输入，不能用 `echo`/`printf` pipe |
| **PO类名大小写不匹配** | 编译失败（找不到符号） | bip-generator生成的类名可能与文件名大小写不一致，如 `WmsMaterialmaster` → 需手动改为 `WmsMaterialMaster` |
| **Header中{po}Detail模板残留** | 编译失败（非法类型） | 代码生成后检查所有 `*Header.java`，将 `{po}Detail` 替换为实际的 `XxxDetail` |
| **Java 8不支持var** | 编译失败（找不到符号：类 var） | bip-generator或模板可能生成 `var` 关键字，需替换为显式类型，如 `var header` → `WmsXxxHeader header` |
| **Converter/Repository缺少PO import** | 编译失败（找不到符号：类 XxxPO）| 生成、复制或**移动 PO 包路径**后，检查 `*Converter.java` 和 `*RepositoryImpl.java` 是否有 `import ...po.sap.XxxPO;` |
| **子表PO不应独立存在** | 数据分散、与表结构不符 | 若接口文档/SQL中子数据以 JSON 存于主表（如 `items_data`），应删除 `XxxItemPO`，在父 PO 中加 `String itemsData` 字段，配合 JSON 序列化 |
| **WMS与SAP报文格式混淆** | DTO结构错误，接口调不通 | WMS格式：`data → header[] → details`；SAP格式：`CONTINFO → BODY → ITEMS`。完全不同的结构，不能复用 |
| **接口方向判断错误** | 全部接口做成同一种模式 | Excel中的"调入/调出"是从WMS视角。必须与业务确认从DMS视角的实际流向，调出=业务模块→DMS→WMS（需RPC），调入=WMS→DMS（Controller直接接收） |
| **缺少BigDecimal import** | 编译失败 | PO中使用了BigDecimal字段但缺少 `import java.math.BigDecimal;`，需手动补充 |
| **bip-generator布尔类型生成`Short`** | 与现有项目约定冲突（`InterfaceSendLog`用`Boolean`） | 将 PO/DTO 中 `Short interfaceSwitch` 改为 `Boolean interfaceSwitch`，与 `SaveInterfaceReq` 保持一致 |
| **bip-generator数据库名构造异常** | `Access denied for user 'xxx'@'%' to database 'c_oem_isscp_{table_name}_db'` | generator 内部将表名拼接为数据库名（如 `c_oem_isscp_ti_interface_accept_log_db`），与真实库名不一致。此错误不影响代码生成，只要 expect 交互完成后输出了文件即可忽略 |
| **bip-generator jar 实际位置在项目根** | `java -jar` 找不到文件 | jar 实际位于 `isscp/bip-generator-1.0-SNAPSHOT-jar-with-dependencies.jar`（项目根），不是 `c-oem-isscp-common-be/` 子目录。用绝对路径调用 |
| **bip-generator调用`setVerifyState`** | 编译失败（找不到符号） | generator模板在`RepositoryImpl`中生成`po.setVerifyState((short) 0)`，但日志/配置类PO无此字段，**直接删除该行** |
| **bip-generator遗漏`pathParam`** | DTO/PO字段与现有约定不一致 | 对照同类表（如`InterfaceSendLog`），若其存在`pathParam`而生成器未产出，需在PO/DTO中手动补全 |
| **ResultUtil / Exception / Handler 中使用魔法值** | 字符串字面量散落各处，难维护、易出错 | **硬性规则**：所有字符串常量（返回码、标记、描述、状态）必须提取到常量类。WMS 用 `WmsConstants`，SAP 用 `SapConstants`。包括 `WmsResultUtil`、`SapResultUtil` 内部的 `"0000"`、`"ok"`、`"S"` 等。常量类放在 `api` 模块 |
| **Controller缺少`SuperController`import** | 编译失败（找不到符号：类SuperController） | generator生成的Controller有`extends SuperController`但缺少`import com.yonyou.oem.common.framework.base.SuperController;`，需手动补充 |
| **现有`InterfaceLogAspect`不区分调入/调出** | 所有日志都写入 `ti_interface_send_log`，调入接口缺少 `accept_log` 记录 | **方案**：`@InterfaceLog` 增加 `boolean inbound() default false`，调入 Controller 显式标记 `inbound = true`。切面读取 `interfaceLog.inbound()` 决定写入 `send_log` 还是 `accept_log`。**不推荐**通过包名推断方向（如含 `.app.controller.`），易被重构破坏。详见 `references/interface-log-inbound-issue.md` |
| **Service catch 中组装失败响应** | AOP 无法区分成功/失败，日志 `interfaceStatus` 永远是成功码；Service 不纯粹 | **方案**：调入接口 Service 校验失败直接 throw `WmsInboundException`/`SapInboundException`，由 AOP 记录异常日志（`interfaceStatus=10041002`），再由 `service` 模块的 `GlobalExceptionHandler` 转换为系统标准响应。Service 只保存接口表并透传下游结果，不组装响应。异常类和处理器均在 `service` 模块，不在 `api` 或 `app`。详见 `references/inbound-interface-exception-pattern.md` |

## 开发顺序

1. 用户提供 SAP/WMS 接口文档（xlsx/pdf）
2. 整理成 **YonBIP 快速新增字段文本**（`编码,名称,类型;` 格式）
3. 用户在 YonBIP「对象建模」粘贴 → 平台自动生成实体并建表
4. 从数据库 `SHOW CREATE TABLE` 导出 SQL 备份到 `c-oem-isscp-common-scripts/scripts/db/patch/`
5. **先生成代码结构 `.md`，用户确认后再运行 `bip-generator` 生成骨架**
6. 在骨架上补充：业务校验、Converter、接口调用逻辑

**字段类型映射**：VARCHAR→文本, TEXT→文本, INT→整数, BIGINT→整数, DECIMAL→数值, DATETIME→日期时间。
**排除 id 和 SuperDO 字段**（ytenantId, creator, createTime, modifier, modifyTime, pubts, dr）。
**数据库表名/字段名全小写**（`ti_sap_sd016`），PO 中用 camelCase（`itemsData`）。

## bip-generator 使用

**位置**：`c-oem-isscp-common/c-oem-isscp-common-be/bip-generator-1.0-SNAPSHOT-jar-with-dependencies.jar`

**运行方式**：
```bash
cd c-oem-isscp-common/c-oem-isscp-common-be
java -jar bip-generator-1.0-SNAPSHOT-jar-with-dependencies.jar
# 输入：表名（如 Ti_Sap_SD016）→ 模块名（如 c-oem-isscp-common）→ 输出目录
```

**构造器参数**：项目名称 `common`，输出目录如 `/tmp/bip-gen-sd016`，表名 `Ti_Sap_SD016`。

**交互式输入必须用 expect**：
```bash
/usr/bin/expect <<'EOF'
set timeout 30
spawn java -jar bip-generator-1.0-SNAPSHOT-jar-with-dependencies.jar
expect "请输入表名"
send "Ti_Wms_AsnCreate\r"
expect "请输入模块名"
send "c-oem-isscp-common\r"
expect "请输入输出目录"
send "/tmp/bip-gen-wms\r"
expect eof
EOF
```

**生成后必须手动调整**：
- **PO**：修正 `YMSEntity` 注解（以 YonBIP 平台实体编码为准，非构造器默认值）
- **PO**：确认 `id` 为 `String`，已实现 `ILogicDelete`
- **PO**：确认类名与文件名大小写一致（bip-generator 可能生成小写类名，如 `WmsMaterialmaster`）
- **PO**：补充缺失的 `import java.math.BigDecimal;`
- **PO**：对照 `scripts/db/patch/*.sql` 或 `SHOW CREATE TABLE` 核对字段，确保 JSON 字段（如 `items_data`/`response_data`）、hex 预留字段、`pubts` 等在 PO 中都有对应属性
- **Repository 接口**：从 `infrastructure` 移到 `service` 模块，方法签名使用 DTO
- **Repository 实现**：添加 `@Transactional(REQUIRES_NEW)`（参考 `SapSd016RepositoryImpl`）
- **Service**：补充业务校验逻辑
- **Converter**：补充 JSON 字段序列化（detailsData），**增加 `toPOList()` 支持 header 多条数据**
- **Controller**：按数据流向合并到 `SapOutboundController`/`WmsOutboundController` 或 `SapInboundController`/`WmsInboundController`
- **验证**：所有手动调整完成后，立即运行 `mvn clean compile -DskipTests` 验证，特别关注 `infrastructure` 模块的 MapStruct 生成器报错（如“No implementation was created”通常意味着 PO import 丢失或类路径变更）

> 日志/配置表（如 `ti_interface_accept_log`/`ti_interface_send_log`）的生成调整细节见 `references/interface-accept-log-generation.md`。
> 当前项目 `InterfaceLogAspect` 不区分调入/调出的方向问题已修复，详见 `references/interface-log-inbound-issue.md`。
> 调入接口异常处理模式（抛异常 + GlobalExceptionHandler）详见 `references/inbound-interface-exception-pattern.md`。
> 多模块重构实战案例（移动 `InterfaceLogService` 与 `InterfaceLogAspect` 解决循环依赖）见 `references/multi-module-refactor-example.md`。

## 模块依赖关系

```
api          ← 无依赖，纯 DTO/接口定义 + repository 接口 + service 接口 + 常量类（WmsConstants/SapConstants）
framework    ← api（AOP 切面、通用注解、框架级组件）
service      ← framework + api（ServiceImpl、repository 接口老位置可逐步迁移到 api、**异常类、全局异常处理器**）
infrastructure ← service + framework + api（repository 实现、PO、Converter）
app          ← service + framework + api + infrastructure（Controller）
bootstrap    ← 全部（Spring Boot 入口）
```

**硬性规则**：
- `service` 绝不依赖 `infrastructure`。ServiceImpl 只通过 Repository 接口操作数据，PO/Converter 仅在 `infrastructure` 中使用。
- **framework 绝不依赖 service**。AOP 切面、通用注解通常放在 `framework`，它们只能引用 `api` 中的接口/ DTO。若切面需要调用 service 实现，有两种做法：  
  1. **标准做法**：在 `api` 中定义对应的服务接口（如 `InterfaceLogService`），由 `service` 模块实现，`framework` 只引用接口。  
  2. **下沉做法**：若接口本身也需在 `service` 模块（如避免过度拆分或与实现紧耦合），则必须将切面一并下沉到 `service`，确保 `framework` 不直接引用 `service` 中的类。

## 按数据流向选择入口

| 方向 | RPC接口 | Controller | 日志表 | 日志AOP位置 |
|------|---------|-----------|--------|------------|
| DMS→外部 | `ISapRemoteService` / `IWmsRemoteService` | `SapOutboundController` / `WmsOutboundController` | `ti_interface_send_log` | `ExternalInterfaceCaller` |
| 外部→DMS | — | `SapInboundController` / `WmsInboundController` | `ti_interface_accept_log` | Controller 方法上 |

## 调出接口 RPC 远程服务

所有调出接口必须提供 RPC 远程服务供业务模块调用：

1. **RPC 接口**（`api` 模块）：`@RemoteCall(RpcConstant.COMMON_REMOTE_CALL)`
2. **RPC 实现**（`service/impl` 模块）：`@Component`，注入具体 Service，调用 `execute()`
3. **业务模块调用**：`@Autowired private IWmsRemoteService wmsRemoteService;`

参考 `ISapRemoteService` / `SapRemoteServiceImpl`。

## 事务与日志规范

- **方向区分**：`@InterfaceLog` 必须在调入 Controller 上显式标记 `inbound = true`，调出默认 `false`。切面通过 `interfaceLog.inbound()` 判断写入 `send_log` 还是 `accept_log`。
- **接口表保存**：`@Transactional(propagation = Propagation.REQUIRES_NEW)`，放 repository 实现类方法上。参考 `SapSd016RepositoryImpl`。
- **日志切面**：`InterfaceLogAspect` 放在 `service` 模块（因引用 `InterfaceLogService` 接口，若放在 `framework` 会导致 `framework -> service` 循环依赖）。必须支持 SpEL 解析（如 `#interfaceCode`）。切面通过 `InterfaceLogService` 接口调用日志保存，而不是直接引用 `InterfaceLogInnerService` 实现类。
- **AOP 自调用**：日志保存带 `@Transactional` 时，必须提取到独立 Spring Bean（如 `InterfaceLogInnerService`）。
- **状态码**：日志表（`send_log` 和 `accept_log`）统一使用 `10041001` = 成功，`10041002` = 失败。WMS 业务层面的 `0000`/`0001` 保留在接口业务表中。
- **useScene**：`不在` `@InterfaceLog` 注解上配置，由切面从 `InterfaceSetDTO.interfaceName` 自动填充。
- **硬性规则**：无论接口/主业务是否异常，**日志和接口数据都必须保存成功**。
- **调入异常模式**：Service 校验失败直接 throw `WmsInboundException`/`SapInboundException`，由 AOP 记录异常日志（`interfaceStatus=10041002`），再由 `service` 模块的 `GlobalExceptionHandler` 转换为系统标准响应。Service 只保存接口表并透传业务结果，不组装响应。异常类和处理器均在 `service` 模块。详见 `references/inbound-interface-exception-pattern.md`。

## 日志字段赋值检查

`InterfaceLogAspect#logInterfaceCall` 填充的字段来源：

| 字段 | 赋值来源 | 是否可能为 NULL |
|------|---------|------------|
| `interfaceNo` | `@InterfaceLog(interfaceCode)` 或 SpEL 解析 | 否（必填） |
| `interfaceName` | `ti_interface_set.interface_name` | 是（配置表为空） |
| `interfaceSwitch` | `ti_interface_set.interface_switch` | 是（配置表为空） |
| `interfaceType` | `ti_interface_set.interface_type` | 是（配置表为空） |
| `interfaceUrl` | `ti_interface_set.request_url` | 是（配置表为空） |
| `useScene` | `@InterfaceLog(useScene)` 默认空字符串 | 否（默认空） |
| `interfaceData` | 入参 JSON 序列化 | 是（无入参） |
| `interfaceResult` | 返回结果 JSON 序列化（仅成功时） | 是（失败时写入 `interfaceMsg`） |
| `interfaceStatus` | 异常判断：`10041001`/成功 `10041002`/失败 | 否 |
| `interfaceTime` | 耗时计算（ms） | 否 |

**分析方法**：对比 `SaveInterfaceReq` 的 setter 调用与 `InterfaceSendLog` PO/数据库表字段，未设置的字段即为缺失。若 setter 已调用但数据库仍为 NULL，说明 `ti_interface_set` 配置表中对应字段为空。

**字段赋值补全检查（`InterfaceLogAspect#logInterfaceCall`）**：

| 字段 | 赋值来源 | 常见遗漏 |
|------|---------|---------|
| `interfaceNo` | `@InterfaceLog(interfaceCode)` / SpEL | 无 |
| `interfaceName` | `InterfaceSetDTO.interfaceName` | 无 |
| `interfaceSwitch` | `InterfaceSetDTO.interfaceSwitch` | 无 |
| `interfaceType` | `InterfaceSetDTO.interfaceType` | 无 |
| `interfaceUrl` | `InterfaceSetDTO.requestUrl` | 无 |
| `logSetId` | `InterfaceSetDTO.id` | **极易遗漏** |
| `useScene` | `InterfaceSetDTO.interfaceName`（切面自动填充，不在注解上配置） | 未在切面中设置 |
| `interfaceData` | 入参 JSON 序列化 | 无 |
| `interfaceResult` | 返回值 JSON（成功）/ exception JSON（失败） | **极易遗漏** |
| `interfaceStatus` | 异常判断 | 无 |
| `interfaceTime` | 耗时计算 | 无 |

**`interfaceResult` 赋值逻辑**：
- 成功：`JSON.toJSONString(result)`（将 Controller 返回值序列化）
- 异常：`JSON.toJSONString(throwable)`（将异常对象序列化，或取 `getMessage()`）

**`useScene` 填充逻辑**：
不在 `@InterfaceLog` 注解中定义 `useScene()` 属性。切面从 `InterfaceSetDTO` 中获取 `interfaceName`，自动填充到 `SaveInterfaceReq.setUseScene(...)`。

```java
// 不推荐此方式
@InterfaceLog(interfaceCode = "SAP_SD016", useScene = "整车销售订单推送")

// 推荐此方式：切面自动使用 interfaceName 填充 useScene
@InterfaceLog(interfaceCode = "SAP_SD016")
```

## DTO 层级结构

### SAP 格式（固定）
- **CONTINFO**: 控制信息（接口ID、源系统、目标系统、数据包ID、时间戳）
- **BODY**: 业务主数据（一行）
- **ITEMS**: 行项目（一行或多行）
- **PRICE/SUBILIST**: 明细条件

### WMS 格式（与SAP完全不同）
- **Request**: `{"data": {"header": [{"details": [...]}]}}`
- **Response**: `{"Response": {"return": {"returnCode", "returnDesc", "returnFlag", "resultInfo"}}}`
- **Header**: 业务主数据字段（多行，每条数据一个header）
- **Details**: 明细数据（序列化为JSON存入 detailsData）

**关键区别**：WMS 的 header 是多条的（List），SAP 的 BODY 只有一行。WMS 没有控制信息层。

## 配置查询字段名

`ExternalInterfaceCaller.callFunction()` 第一步查 `ti_interface_set`：
- `interfaceNo`（不是 `interfaceCode`）
- `requestUrl`（不是 `url` 或 `interfaceUrl`）
- `appKey` / `appSecret`

参考 `ExternalInterfaceCaller` 完整实现。

## 接口数据表规范

**表命名**：
- SAP: `Ti_Sap_{接口编码}`，如 `Ti_Sap_SD016`
- WMS: `Ti_Wms_{接口名}`，如 `Ti_Wms_AsnCreate`

**设计原则**：
- 按接口文档字段创建列
- 复杂对象（ITEMS、details）用 JSON 存储
- 保留外部系统返回码、返回消息、异常信息字段
- 包含 SuperDO 审计字段
- **所有字段和表必须加 COMMENT 注释**

**注释规范**：
- 普通字段：中文含义（如 `'订单类型'`）
- 枚举字段：中文 + 枚举值（如 `'生产模式（CBU/CKD/SKD/DKD/REP）'`）
- 固定值字段：中文 + 固定值（如 `'接口ID，固定值 SD016'`）
- JSON 字段：中文 + 来源类（如 `'行项目JSON（List<SapSd016Item>）'`）
- SAP/WMS 返回字段：中文 + 更新来源（如 `'返回码（S成功/E错误）'`）
- 表级：`COMMENT='SD016 整车/退货销售订单创建接口数据表'`

## 数据库操作：IYmsJdbcApi + DO/PO

**不存在**不通过 DO 的插入/更新/删除。无 JdbcTemplate、MyBatis XML。

**关键要点**：
- 插入：设 `_status(VOStatus.NEW)`、`ytenantId`、`creator`、`createTime`、`modifier`、`modifyTime`
- 更新：设 `_status(VOStatus.UPDATED)`、`modifier`、`modifyTime`
- 查询：设 `dr((short) 0)` 和 `ytenantId`

参考 `InterfaceSetRepositoryImpl`、`InterfaceSendLogRepositoryImpl`。

## 接口编码规范

统一使用 **`SAP_{接口编码}`** 或 **`WMS_{接口编码}`**：
- 调出：`SAP_SD016`、`WMS_ASNCREATE`
- 调入：`SAP_FICO060B`、`WMS_PACKRESULT`

使用位置：
- `ServiceImpl` 的 `INTERFACE_CODE` 常量
- `@InterfaceLog(interfaceCode = "SAP_SD016")`
- `ti_interface_set` 表的 `interface_no`
- HTTP 测试脚本：`sap-sd016-test.http`、`wms-asncreate-test.http`

## 泛型避免类型转换

```java
public <T, R> R callFunction(String interfaceCode, T request, Class<R> responseType)
```

## 测试策略

- `SapSd016RepositoryImpl` 强依赖 `IYmsJdbcApi`，**无法在 JUnit 中启动真实实现**
- 对运行中的 YMS 服务发 HTTP 请求是唯一真实测试 Repository 落库的方式
- `.http` 文件放在 `c-oem-isscp-common/c-oem-isscp-common-scripts/scripts/http/{接口编码}-test.http`
- 需携带 `Cookie: yht_access_token=xxx`

## 其他硬性规则

- `JsonResult.success()` 不存在，使用 `new JsonResult<>(response)`
- `DateTimeFormatter` 提取为 `private static final` 复用
- `ExternalInterfaceCaller` 未实现时抛 `UnsupportedOperationException`，不返回 null
- 枚举值补充到 `api` 层的 `enums/sap/` 或 `enums/wms/`，**禁止放在 service**
- HTTP 测试脚本：YMS 模块部署在根路径，无需加模块前缀

## 核心表

| 表名 | 用途 | 对应 DO |
|------|------|---------|
| `ti_interface_send_log` | 调出日志(DMS→外部) | InterfaceSendLog |
| `ti_interface_accept_log` | 调入日志(外部→DMS) | InterfaceAcceptLog |
| `ti_interface_set` | 接口配置(URL、密钥等) | InterfaceSet |

## 核心 Repository

| Repository | 关键方法 | 返回值 |
|-----------|---------|--------|
| InterfaceSetRepository | `selectByCode(String interfaceNo)` | `List<InterfaceSetDTO>` |
| InterfaceSendLogRepository | `saveLog(SaveInterfaceReq req)` | void |

## Example：新增调出接口（WMS_ASNCREATE）

1. 用户提供 WMS 接口文档
2. 整理 YonBIP 快速新增字段文本
3. YonBIP「对象建模」建实体
4. `SHOW CREATE TABLE` 导出 SQL 备份
5. **生成代码结构 `.md`，用户确认后**运行 `bip-generator` 生成骨架
6. 调整代码（PO 注解、类名大小写、Repository 位置、@Transactional、Converter、BigDecimal import）
7. 添加 HTTP 测试脚本
8. `IWmsRemoteService` 新增方法声明
9. `WmsRemoteServiceImpl` 新增调用逻辑
10. 补充枚举到 `api/enums/wms/`

## Example：新增调入接口（WMS_PACKRESULT）

前 6 步同上（见「新增调出接口」）。
7. 添加 HTTP 测试脚本
8. `WmsInboundController` 添加方法，标注 `@InterfaceLog(interfaceCode = "WMS_PACKRESULT", inbound = true)`（必须显式标记 `inbound = true`）
9. Service 中校验失败抛 `WmsInboundException`，只保存接口表并透传业务结果，不组装默认成功响应
10. `service` 模块 `GlobalExceptionHandler` 处理 `WmsInboundException`，转换为 `WmsResponseDTO`
11. 补充枚举到 `api/enums/wms/`
12. 无需修改 `InterfaceLogAspect`

详见 `references/inbound-interface-exception-pattern.md`。

## 代码参考位置

| 组件 | 参考文件 |
|------|---------|
| 调出 Controller | `c-oem-isscp-common-app/.../wms/WmsOutboundController.java` |
| 调入 Controller | `c-oem-isscp-common-app/.../wms/WmsInboundController.java` |
| RPC Service 接口 | `c-oem-isscp-common-api/.../IWmsRemoteService.java` |
| RPC Service 实现 | `c-oem-isscp-common-be/dev-c-oem-isscp-common-service/.../WmsRemoteServiceImpl.java` |
| 外部接口调用器 | `c-oem-isscp-common-be/dev-c-oem-isscp-common-service/.../ExternalInterfaceCaller.java` |
| 日志切面 | `c-oem-isscp-common-service/.../aop/InterfaceLogAspect.java` （注：因循环依赖约束，已从 framework 下沉至 service） |
| 日志注解 | `c-oem-isscp-common-framework/.../annotation/InterfaceLog.java` |
| 日志 Service 接口 | `c-oem-isscp-common-service/.../api/service/InterfaceLogService.java` （注：已从 api 移至 service，与其实现同模块） |
| 接口配置 Repository | `c-oem-isscp-common-api/.../service/repository/InterfaceSetRepository.java` |
| Repository 示例 | `c-oem-isscp-common-be/dev-c-oem-isscp-common-infrastructure/.../wms/WmsAsncreateRepositoryImpl.java` |
| 调入异常处理器 | `c-oem-isscp-common-service/.../handler/GlobalExceptionHandler.java` （注：已从 `app` 下沉至 `service`，与异常类同模块） |