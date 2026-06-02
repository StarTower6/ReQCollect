"""PM Agent configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PM Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9900

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_timeout: int = 10000

    rag_top_k: int = 5
    rag_model: str = "deepseek-chat"

    chunk_max_size: int = 800
    chunk_overlap: int = 100

    redis_url: str = "redis://localhost:6379"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "pm_agent"
    mysql_password: str = "pm_agent_pass"
    mysql_database: str = "pm_agent"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    sufficiency_threshold: float = 0.75


config = Settings()
