from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # silently ignore unknown env vars (e.g. HF_TOKEN leftovers)
    )

    # LLM — defaults to Groq; swap base_url + key for OpenAI or any compatible provider
    llm_api_key: str
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"

    database_url: str = "sqlite:///./bizquery.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    chroma_dir: str = "./chroma_db"
    upload_dir: str = "./uploads"

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


try:
    settings = Settings()
except Exception as e:
    raise SystemExit(
        f"\n  Failed to load settings: {e}\n"
        "    Copy backend/.env.example → backend/.env and fill in your values.\n"
        "    At minimum: LLM_API_KEY=<your-groq-key>\n"
    )
