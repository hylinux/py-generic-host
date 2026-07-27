# py-generic-host

> Production-ready Python Generic Host Framework (.NET Style)

基于 **FastAPI + Dependency Injector + OpenTelemetry + Structlog**
构建的 Python 通用宿主框架（Generic Host）。

本项目借鉴 ASP.NET Core Generic Host 设计理念，为 Python 提供：

- 生命周期管理（Host）
- 后台服务（Hosted Service）
- 依赖注入（Dependency Injection）
- Web Hosting（FastAPI + Uvicorn）
- 配置管理（Pydantic Settings）
- 健康检查（Health Checks）
- OpenTelemetry 可观测性
- Structured Logging

帮助开发者快速构建：

- Web API
- AI Agent
- 微服务
- Worker Service
- 定时任务
- 数据采集服务
- 企业级后台系统

---

# 核心特性

## Generic Host

统一管理应用生命周期：

```python
host = builder.build()

await host.run_async()
```

支持：

- Startup
- Graceful Shutdown
- Application Lifetime
- Signal Handling
- Background Services

---

## Hosted Service

类似 ASP.NET Core 的：

```csharp
BackgroundService
```

Python 版本：

```python
class SampleWorker(
    BackgroundService,
):

    async def execute_async(
        self,
        stopping: asyncio.Event,
    ) -> None:

        while not stopping.is_set():

            print("working")

            await asyncio.sleep(5)
```

注册：

```python
builder.add_hosted_service(
    SampleWorker(),
)
```

适用于：

- 消息消费
- Queue Worker
- 定时任务
- 数据同步
- AI Agent

---

## Dependency Injection

基于：

```text
dependency-injector
```

提供：

- Singleton
- Factory
- Resource

示例：

```python
class AppContainer(
    containers.DeclarativeContainer,
):

    user_service = providers.Factory(
        UserService,
    )
```

---

## FastAPI Hosting

内置：

```text
FastAPI
+
Uvicorn
+
Generic Host
```

集成。

```python
builder = WebHostBuilder()
```

自动完成：

- FastAPI 创建
- Middleware 管理
- Uvicorn Hosting
- Application Lifetime 集成

---

## Health Checks

内置：

```python
HealthCheckService
```

支持：

- Liveness
- Readiness
- 自定义检查

示例：

```python
class RedisHealthCheck(
    IHealthCheck,
):
    ...
```

---

## Structured Logging

基于：

```python
structlog
```

构建结构化日志。

支持：

- JSON 日志
- 请求上下文
- request_id
- trace_id
- span_id

---

## OpenTelemetry

支持：

```text
Tracing
Metrics
Logs
```

集成：

- FastAPI
- HTTPX
- SQLAlchemy
- Redis
- AsyncIO

Exporter：

- OTLP
- Prometheus

---

# 安装

## 使用 Wheel 安装

构建：

```bash
uv build --wheel
```

安装：

```bash
uv pip install dist/*.whl
```

或者：

```bash
pip*install dist/*.whl
```

---

## 开发模式

```bash
uv pip install -e .
```

---

# 项目结构

推荐结构：

```text
my-app
│
├── app
│   ├── api
│   ├── services
│   ├── container.py
│   ├── settings.py
│   └── main.py
│
├── tests
│
└── pyproject.toml
```

---

# 配置管理

框架使用：

```python
pydantic-settings
```

管理配置。

---

## settings.py

```python
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class ExternalApiSettings(
    BaseModel,
):
    base_url: str = ""
    timeout: float = 5.0


class AppSettings(
    BaseSettings,
):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="APP_",
    )

    env: str = "dev"

    http_host: str = "0.0.0.0"

    http_port: int = 8080

    external: ExternalApiSettings
```

---

## .env

```env
APP_ENV=dev

APP_HTTP_PORT=8080

APP_EXTERNAL__BASE_URL=https://api.contoso.com

APP_EXTERNAL__TIMEOUT=10
```

---

# Dependency Injection

## Container

```python
class AppContainer(
    containers.DeclarativeContainer,
):

    settings = providers.Singleton(
        AppSettings,
    )

    external_settings = providers.Singleton(
        lambda s: s.external,
        settings,
    )
```

---

## Service

```python
class ExternalApiClient:

    def __init__(
        self,
        settings: ExternalApiSettings,
    ) -> None:

        self._base_url = (
            settings.base_url
        )
```

---

# 创建 Web API

## Router

```python
router = APIRouter()


@router.get("/ping")
async def ping():
    return {"status": "ok"}
```

---

## Startup

```python
host = (
    WebHostBuilder()
    .use_container(container)
    .configure_endpoints(
        lambda ctx, app:
            app.include_router(router)
    )
    .build()
)

await host.run_async()
```

---

# Health Checks

注册：

```python
class DatabaseHealthCheck(
    IHealthCheck,
):
    ...
```

添加到：

```python
health_service = providers.Singleton(
    HealthCheckService,
    checks=providers.List(
        db_check,
    ),
)
```

---

# 典型应用场景

适用于：

✅ FastAPI Web API

✅ 微服务

✅ Agent Framework

✅ Worker Service

✅ 定时任务

✅ 数据同步服务

✅ 企业级后台系统

✅ 数据平台工具服务

---

# 设计理念

借鉴：

- ASP.NET Core Generic Host
- ASP.NET Core WebHost
- BackgroundService
- IHostedService
- Microsoft Dependency Injection
- OpenTelemetry

目标是在 Python 生态中提供接近 .NET 的开发体验。

---

# Roadmap

当前：

- [x] Generic Host
- [x] BackgroundService
- [x] DI Container
- [x] FastAPI Hosting
- [x] Pydantic Settings
- [x] Health Checks
- [x] OpenTelemetry

规划：

- [ ] Logging Builder
- [ ] Telemetry Builder
- [ ] Metrics Builder
- [ ] Distributed Tracing Extensions
- [ ] Azure Monitor Integration
- [ ] Azure App Configuration Integration

---

# License

Apache License

---

# Author

**HongWei Guo**

---

> Bring the .NET Generic Host experience to Python.
