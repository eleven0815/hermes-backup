# InterfaceLogAspect 调入/调出日志方向问题（已修复）

## 问题描述

当前项目中的 `InterfaceLogAspect` 切面拦截所有带有 `@InterfaceLog` 注解的方法，但**仅调用 `InterfaceSendLogRepository.saveLog()`**，导致：
- `ExternalInterfaceCaller.callFunction()` 上的 `@InterfaceLog` → 正确写入 `ti_interface_send_log` （调出）
- `WmsInboundController` / `SapInboundController` 方法上的 `@InterfaceLog` → 错误地写入 `ti_interface_send_log` （应该写入 `ti_interface_accept_log`）

## 最终实现方案

### 1. `@InterfaceLog` 增加 `inbound` 属性

```java
public @interface InterfaceLog {
    String interfaceCode();
    boolean inbound() default false;
}
```

调入 Controller 显式标记：`@InterfaceLog(interfaceCode = "WMS_PACKRESULT", inbound = true)`

**不推荐**通过包名推断方向（如包名含 `.app.controller.`），易被重构破坏，显式标记更可靠。

### 2. `InterfaceLogService` 增加 `isInbound` 参数

```java
void saveLog(SaveInterfaceReq saveReq, Object result, Throwable exception, long costTime, boolean isInbound);
```

### 3. `InterfaceLogInnerService` 双 Repository 分发

注入 `InterfaceAcceptLogRepository`，根据 `isInbound` 分发：
- `true` → `interfaceAcceptLogRepository.saveLog(saveReq)`
- `false` → `interfaceSendLogRepository.saveLog(saveReq)`

统一状态码 `10041001`/成功、`10041002`/失败，不区分系统。

### 4. `InterfaceLogAspect` 读取 `inbound()`

```java
boolean isInbound = interfaceLog.inbound();
```

### 5. `useScene` 自动填充

**不在 `@InterfaceLog` 上配置 `useScene`**。切面从 `InterfaceSetDTO.interfaceName` 自动获取并写入 `SaveInterfaceReq.setUseScene(interfaceName)`。

---

## 已完成修复的文件清单

| 文件 | 变更 |
|------|------|
| `framework/.../annotation/InterfaceLog.java` | 新增 `boolean inbound() default false` |
| `service/.../api/service/InterfaceLogService.java` | `saveLog` 方法签名增加 `boolean isInbound` |
| `service/.../impl/InterfaceLogInnerService.java` | 注入双 Repository，按 `isInbound` 分发 |
| `service/.../aop/InterfaceLogAspect.java` | 读取 `inbound()`、`useScene` 使用 `interfaceName` |
| `app/.../handler/GlobalExceptionHandler.java` | 新建，处理调入异常 |
| `api/.../exception/wms/WmsInboundException.java` | 新建 |
| `api/.../exception/sap/SapInboundException.java` | 新建 |
| `api/.../util/wms/WmsResultUtil.java` | 新建 |
| `api/.../util/sap/SapResultUtil.java` | 新建 |
| `app/.../wms/WmsInboundController.java` | 5 个方法补充 `inbound = true` |
| `app/.../sap/SapInboundController.java` | 1 个方法补充 `inbound = true` |
