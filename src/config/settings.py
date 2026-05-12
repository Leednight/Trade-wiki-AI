"""全局配置 - 基于 pydantic-settings，从 .env 文件和环境变量读取"""

from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class FeishuSettings(BaseSettings):
    """飞书 Bot 配置"""

    model_config = SettingsConfigDict(env_prefix="FEISHU_")

    app_id: str = ""
    app_secret: str = ""
    verification_token: str = ""
    encrypt_key: str = ""


class OllamaSettings(BaseSettings):
    """本地 Ollama 模型配置"""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b-instruct-q4_K_M"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60  # 秒


class DeepSeekSettings(BaseSettings):
    """DeepSeek API 配置"""

    model_config = SettingsConfigDict(env_prefix="DEEPSEEK_")

    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class OpenAISettings(BaseSettings):
    """OpenAI API 配置 (备用)"""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class EmbeddingSettings(BaseSettings):
    """向量模型配置"""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    model: str = "BAAI/bge-m3"
    device: str = "cuda"
    normalize_embeddings: bool = True


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    model_config = SettingsConfigDict(env_prefix="")

    sqlite_db_path: str = str(DATA_DIR / "db" / "trade_wiki.db")
    chromadb_path: str = str(DATA_DIR / "chromadb")


class AppSettings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    data_dir: str = str(DATA_DIR)
    encryption_key: str = ""


class Settings(BaseSettings):
    """所有配置的聚合入口"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = AppSettings()
    feishu: FeishuSettings = FeishuSettings()
    ollama: OllamaSettings = OllamaSettings()
    deepseek: DeepSeekSettings = DeepSeekSettings()
    openai: OpenAISettings = OpenAISettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    database: DatabaseSettings = DatabaseSettings()


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
