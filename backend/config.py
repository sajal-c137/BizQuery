from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./bizquery.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

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
