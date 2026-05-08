from openai import AsyncOpenAI

from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

_BASE_SYSTEM_PROMPT = (
    "You are BizQuery, an AI-powered business analytics assistant. "
    "You help users understand and analyze their business data. "
    "When data context is provided, use it to give precise, data-driven answers. "
    "Show calculations when relevant. Be concise but thorough."
)


def _format_data_context(ctx: dict) -> str:
    lines = [
        f"=== DATA SOURCE: {ctx['source_id']} ({ctx['row_count']} rows) ===",
        "",
        "COLUMNS:",
    ]
    for col in ctx["columns"]:
        if "stats" in col:
            s = col["stats"]
            lines.append(
                f"  {col['name']} ({col['dtype']}): "
                f"min={s['min']}, max={s['max']}, mean={s['mean']}, sum={s['sum']}"
            )
        elif "unique_values" in col:
            lines.append(
                f"  {col['name']} ({col['dtype']}): "
                f"{col['unique_count']} unique — {col['unique_values']}"
            )
        else:
            lines.append(f"  {col['name']} ({col['dtype']}): {col['unique_count']} unique values")

    lines += ["", "SAMPLE ROWS (first 5):"]
    for row in ctx["sample_rows"]:
        lines.append(f"  {row}")

    return "\n".join(lines)


async def get_ai_response(history: list[dict], data_context: dict | None = None) -> str:
    system_content = _BASE_SYSTEM_PROMPT
    if data_context:
        system_content += "\n\n" + _format_data_context(data_context)

    messages = [{"role": "system", "content": system_content}] + history
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
    )
    return response.choices[0].message.content
