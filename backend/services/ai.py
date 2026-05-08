from config import settings
from services.openai_client import client

_BASE_SYSTEM_PROMPT = (
    "You are BizQuery, a business analytics assistant. "
    "Rules: answer in 1-2 sentences, state each fact exactly once, never self-correct or repeat. "
    "Format: lead with the direct answer, end with one optional follow-up offer. "
    "Use only the pre-computed stats from context — do not recalculate."
)


def _format_rag_context(chunks: list[dict]) -> str:
    lines = ["=== RETRIEVED DOCUMENT CONTEXT ==="]
    for i, chunk in enumerate(chunks, 1):
        source = chunk["metadata"].get("filename", "unknown")
        lines.append(f"\n[{i}] Source: {source} (relevance: {chunk['score']})")
        lines.append(chunk["text"])
    return "\n".join(lines)


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

    if ctx.get("group_stats"):
        lines.append("")
        lines.append("GROUPED TOTALS:")
        for cat, groups in ctx["group_stats"].items():
            lines.append(f"  By {cat}:")
            for val, stats in groups.items():
                stat_str = ", ".join(f"{k}={v}" for k, v in stats.items())
                lines.append(f"    {val}: {stat_str}")
    return "\n".join(lines)


async def get_ai_response(
    history: list[dict],
    data_context: dict | None = None,
    rag_context: list[dict] | None = None,
) -> str:
    system_content = _BASE_SYSTEM_PROMPT
    if rag_context:
        system_content += "\n\n" + _format_rag_context(rag_context)
    if data_context:
        system_content += "\n\n" + _format_data_context(data_context)

    messages = [{"role": "system", "content": system_content}] + history
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
    )
    return response.choices[0].message.content
