# 调入接口异常处理模式

## 问题背景

调入接口（WMS/SAP → DMS）的 Service 原有实现中，校验失败或业务异常时在 `try-catch` 中组装失败响应并返回，不 throw。这导致：
- AOP 无法区分成功/失败（都是正常返回值）
- 日志 `interfaceStatus` 永远是成功码
- Service 不纯粹，混杂了响应组装逻辑

## 新模式：抛异常 + 全局处理器

调入接口的 Service 应该只做一件事：**透传**。参数校验失败时抛出自定义异常，由 AOP 记录日志 + 全局异常处理器转换为对应系统的标准响应。

### 调用链

```
WMS/SAP → Controller(@InterfaceLog inbound=true)
    ↓
AOP 拦截 → 记录 ti_interface_accept_log（异常也记录，status=10041002）
    ↓
Service.processInbound()
    ↓
  ① 参数校验 → 失败抛 WmsInboundException / SapInboundException
  ② 保存接口业务表（REQUIRES_NEW）
  ③ 调用下游业务 → 透传其返回值（TODO 阶段用默认成功响应占位）
  ④ 更新接口业务表
    ↓
正常返回 → Controller 原样返回业务值
    ↓
异常 → GlobalExceptionHandler 捕获 → 转换为标准失败响应
```

### 关键约束

1. **Service 不组装失败响应**，失败统一 throw
2. **AOP 记录异常日志**，异常时 `interfaceStatus=10041002`，`interfaceMsg` 写入异常信息
3. **全局处理器在 `service` 模块**（已从 `app` 下沉），转换异常为系统标准响应（`WmsResponseDTO` / `SapFico0601ResponseDTO`）
4. **DMS 不调用 ResultUtil**，ResultUtil 只供下游业务模块使用
5. **Service 只保存接口表，不组装返回值**。业务模块返回什么，Service 就透传什么。TODO 占位阶段也不应保留默认成功响应组装方法。

### 自定义异常

**异常类必须放在 `service` 模块**，不能放在 `api`。`api` 模块只能有接口、DTO、常量，不能有业务异常。

**WmsInboundException**（在 `service` 模块 `com.yonyou.oem.common.exception.wms`）：
```java
public class WmsInboundException extends RuntimeException {
    private final String returnCode;
    private final String returnDesc;
    private final String returnFlag;
    // 构造器...
}
```

**SapInboundException** 需携带请求上下文（`packmsgid` + `intfid`），以便构建完整的 SAP 错误响应：
```java
public class SapInboundException extends RuntimeException {
    private final String code;
    private final String msg;
    private final String packmsgid;
    private final String intfid;
    // 构造器...
}
```

### GlobalExceptionHandler

**必须放在 `service` 模块**（已从 `app` 下沉），与自定义异常同模块，避免 `app` 引用 `service` 中的异常类。

    @ExceptionHandler(WmsInboundException.class)
    @ResponseBody
    public WmsResponseDTO handleWmsInboundException(WmsInboundException e) {
        return WmsResultUtil.fail(e.getReturnCode(), e.getReturnDesc());
    }

    @ExceptionHandler(SapInboundException.class)
    @ResponseBody
    public SapFico0601ResponseDTO handleSapInboundException(SapInboundException e) {
        return SapResultUtil.fail(e.getPackmsgid(), e.getIntfid(), e.getCode(), e.getMsg());
    }
}
```

### ResultUtil 规范

每个系统一个 ResultUtil，供下游业务模块使用，DMS 本身不调用。

**硬性规则：ResultUtil 中不得有魔法值**。所有字符串常量必须提取到对应系统的常量类中：
- WMS: `WmsConstants.RETURN_CODE_SUCCESS`、`WmsConstants.RETURN_FLAG_SUCCESS`、`WmsConstants.RETURN_DESC_SUCCESS` 等
- SAP: `SapConstants.SAP_CODE_SUCCESS`、`SapConstants.SAP_CODE_ERROR` 等

常量类放在 `api` 模块，供下游业务模块和 DMS 共同引用。
