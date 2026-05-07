from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./bizquery.db"
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


try:
    settings = Settings()
except Exception:
    raise SystemExit(
        "\n  Missing required environment variables.\n"
        "    Copy backend/.env.example → backend/.env and fill in your values.\n"
        "    At minimum: OPENAI_API_KEY=sk-...\n"
    )
