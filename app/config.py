from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ===== LLM (Anthropic Claude) =====
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"

    # ===== Embedding (Voyage AI) =====
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3-large"

    # ===== Backend callback =====
    callback_base_url: str = "http://localhost:8080"

    # ===== AWS S3 (선택) =====
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    aws_s3_bucket: str = "memora-uploads"

    # ===== FAISS =====
    vector_store_path: str = "./vector_store"


settings = Settings()
