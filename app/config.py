"""PM Agent configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ReQCollect"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9900

    # LLM (OpenAI-compatible API, e.g. DeepSeek, OpenAI, etc.)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    # PM Agent
    sufficiency_threshold: float = 0.75
    data_dir: str = "./pm_data"

    # MySQL (asyncmy)
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_user: str = "reqcollect"
    mysql_password: str = ""
    mysql_database: str = "reqcollect"
    mysql_pool_size: int = 20
    mysql_max_overflow: int = 10

    # Force MySQL (if True, fail on connection error instead of falling back)
    mysql_required: bool = False


config = Settings()
