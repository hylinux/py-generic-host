from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OtelSettings(BaseModel):
    service_name: str = "py-generic-host"
    otlp_endpoint: str = "http://localhost:4317"
    sample_ratio: float = 1.0



class ExternalApiSettings(BaseModel):
    base_url: str = "http://localhost"
    timeout: float = 5.0
    api_key: SecretStr = SecretStr("")



class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="APP_",
        extra="ignore",
    )

    env: str = "dev"
    service_name: str = "py-generic-host"
    http_host: str = "0.0.0.0" # noqa: S104
    http_port: int = 8080
    log_level: str = "INFO"
    otel: OtelSettings = OtelSettings()
    external: ExternalApiSettings = ExternalApiSettings()

