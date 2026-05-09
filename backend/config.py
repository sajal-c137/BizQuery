from pydantic_settings import BaseSettings, SettingsConfigDict

from logger import get_logger

log = get_logger("config")


class Settings(BaseSettings):
    # load from .env in dev, env vars in docker
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # ignore unknown vars (e.g. stale HF_TOKEN)
        extra="ignore",
    )

    # LLM creds — defaults work for Groq
    # swap base_url + key for OpenAI / OpenRouter / Together / etc
    llm_api_key: str
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"

    # storage paths
    database_url: str = "sqlite:///../database/bizquery.db"
    chroma_dir: str = "../database/chroma_db"
    upload_dir: str = "./uploads"

    # CORS — comma separated list
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    def get_cors_origins(self) -> list[str]:
        # split + strip whitespace, drop empties
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# load once on import; bail loudly if required vars are missing
try:
    settings = Settings()
    log.info("settings loaded (model=%s, db=%s)", settings.llm_model, settings.database_url)
except Exception as e:
    # raise SystemExit so uvicorn refuses to start with a clear message
    raise SystemExit(
        f"\n  Failed to load settings: {e}\n"
        "    Copy backend/.env.example -> backend/.env and fill in your values.\n"
        "    At minimum: LLM_API_KEY=<your-groq-key>\n"
    )
