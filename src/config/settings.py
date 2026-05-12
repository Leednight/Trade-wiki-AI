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


class SiliconFlowSettings(BaseSettings):
    """硅基流动 API 配置 (主力云端模型)

    官网: https://siliconflow.cn
    OpenAI 兼容格式，支持多种开源模型:
    - deepseek-ai/DeepSeek-V3         通用推理，性价比高
    - deepseek-ai/DeepSeek-R1         深度推理，带思维链
    - Qwen/Qwen2.5-72B-Instruct       中文理解强
    - Qwen/Qwen2.5-7B-Instruct        轻量快速
    - Pro/Qwen/Qwen2.5-VL-7B-Instruct 视觉理解
    """

    model_config = SettingsConfigDict(env_prefix="SILICONFLOW_")

    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "deepseek-ai/DeepSeek-V3"
    vl_model: str = "Pro/Qwen/Qwen2.5-VL-7B-Instruct"  # 视觉理解模型
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class OpenAISettings(BaseSettings):
    """OpenAI API 配置 (备用，可选)"""

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
    provider: str = "local"  # local (本地GPU) / siliconflow (远程API)


class BinanceSettings(BaseSettings):
    """币安 API 配置 (数字货币行情)"""

    model_config = SettingsConfigDict(env_prefix="BINANCE_")

    base_url: str = "https://api.binance.com"
    api_key: str = ""  # 公开行情无需API Key
    api_secret: str = ""  # 需要私有数据时填写


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
    siliconflow: SiliconFlowSettings = SiliconFlowSettings()
    openai: OpenAISettings = OpenAISettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    binance: BinanceSettings = BinanceSettings()
    database: DatabaseSettings = DatabaseSettings()


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
