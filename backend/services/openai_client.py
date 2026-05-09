from openai import AsyncOpenAI

from config import settings
from logger import get_logger

log = get_logger("llm")

# single shared async client — reused across requests
# works with any OpenAI-compatible provider (Groq is the default)
client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)

log.info("LLM client ready (base_url=%s)", settings.llm_base_url)
