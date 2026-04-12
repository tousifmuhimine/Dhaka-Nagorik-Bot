from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Dhaka Nagorik Bot", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    flet_host: str = Field(default="127.0.0.1", alias="FLET_HOST")
    flet_port: int = Field(default=8550, alias="FLET_PORT")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str = Field(default="", alias="SUPABASE_JWT_SECRET")

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    email_user: str = Field(default="", alias="EMAIL_USER")
    email_password: str = Field(default="", alias="EMAIL_PASSWORD")
    email_smtp_host: str = Field(default="smtp.gmail.com", alias="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, alias="EMAIL_SMTP_PORT")
    email_from_name: str = Field(default="Dhaka Nagorik Bot", alias="EMAIL_FROM_NAME")
    email_sender: str = Field(default="noreply@dhakanagorikbot.com", alias="EMAIL_SENDER")

    enable_email: bool = Field(default=True, alias="ENABLE_EMAIL")
    enable_tavily_search: bool = Field(default=True, alias="ENABLE_TAVILY_SEARCH")
    enable_advanced_rag: bool = Field(default=False, alias="ENABLE_ADVANCED_RAG")

    policy_directory: Path = Field(default=Path.cwd(), alias="POLICY_DIRECTORY")
    document_output_dir: Path = Field(default=Path.cwd() / "generated_docs", alias="DOCUMENT_OUTPUT_DIR")
    local_storage_path: Path = Field(default=Path.cwd() / "storage", alias="LOCAL_STORAGE_PATH")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def has_email_config(self) -> bool:
        return bool(self.email_user and self.email_password and self.enable_email)

    @property
    def has_tavily_config(self) -> bool:
        return bool(self.tavily_api_key and self.enable_tavily_search)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.document_output_dir.mkdir(parents=True, exist_ok=True)
    settings.local_storage_path.mkdir(parents=True, exist_ok=True)
    return settings
