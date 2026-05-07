from openai import AsyncOpenAI

from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = (
    "You are BizQuery, a helpful AI assistant. "
    "Answer questions clearly and concisely."
)


async def get_ai_response(history: list[dict]) -> str:
    """Send conversation history to OpenAI and return the assistant reply."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
    )
    return response.choices[0].message.content
