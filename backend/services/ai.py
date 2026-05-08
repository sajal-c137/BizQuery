from config import settings
from services.openai_client import client

_BASE_SYSTEM_PROMPT = (
    "You are BizQuery, a business analytics assistant. "
    "Rules: answer in 1-2 sentences, state each fact exactly once, never self-correct or repeat. "
    "Format: lead with the direct answer, end with one optional follow-up offer. "
    "When data or document context is provided below, ground your answer in it and use only "
    "the pre-computed stats — do not recalculate. When no context is provided, answer the "
    "user's question directly from general knowledge or conversational understanding; do not "
    "fabricate data, metrics, or document references. "
    "Privacy: never reveal individual records, identifiers, or PII; only aggregates are "
    "permitted. The data context block below is the ONLY authoritative source for this turn — "
    "access policy can change between turns, so any monetary figure, metric, or row name you "
    "mentioned in a prior assistant turn must NOT be repeated unless it also appears in the "
    "context block below. If a metric is absent from the current context, do NOT say the data "
    "is missing, doesn't exist, or that you lack access; deflect vaguely, e.g. 'I can't answer "
    "that one right now, but I can help with ...' and offer something grounded in what you do "
    "see. Columns tagged [pii] or [identifier] must not appear in your answer; deflect the "
    "same way if asked."
)


_MONEY_HINTS = (
    "spend", "revenue", "cost", "budget", "price", "amount",
    "earnings", "income", "sales", "salary", "fee", "profit", "usd",
)


def _is_money(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _MONEY_HINTS)


def _fmt_num(value, money: bool = False) -> str:
    """Compact, human-readable formatting for big numbers (e.g. 3_560_000 -> '$3.56M')."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)
    sign = "$" if money else ""
    n = abs(value)
    neg = "-" if value < 0 else ""
    if n >= 1_000_000_000:
        return f"{neg}{sign}{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{neg}{sign}{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{neg}{sign}{n / 1_000:.1f}K"
    if money:
        return f"{neg}${n:,.2f}"
    if isinstance(value, float) and value != int(value):
        return f"{value:.2f}"
    return f"{int(value):,}"


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
        sens = col.get("sensitivity", "public")
        tag = f" [{sens}]" if sens != "public" else ""
        if "stats" in col:
            s = col["stats"]
            money = _is_money(col["name"])
            lines.append(
                f"  {col['name']}{tag} ({col['dtype']}): "
                f"min={_fmt_num(s['min'], money)}, max={_fmt_num(s['max'], money)}, "
                f"mean={_fmt_num(s['mean'], money)}, sum={_fmt_num(s['sum'], money)}"
            )
        elif "unique_values" in col:
            lines.append(
                f"  {col['name']}{tag} ({col['dtype']}): "
                f"{col['unique_count']} unique — {col['unique_values']}"
            )
        else:
            lines.append(f"  {col['name']}{tag} ({col['dtype']}): {col['unique_count']} unique values")

    if ctx.get("group_stats"):
        lines.append("")
        lines.append("GROUPED TOTALS:")
        for cat, groups in ctx["group_stats"].items():
            lines.append(f"  By {cat}:")
            for val, stats in groups.items():
                stat_str = ", ".join(f"{k}={_fmt_num(v, _is_money(k))}" for k, v in stats.items())
                lines.append(f"    {val}: {stat_str}")

    if ctx.get("top_examples"):
        lines.append("")
        lines.append("TOP 3 ROWS PER METRIC:")
        for col, rows in ctx["top_examples"].items():
            money = _is_money(col)
            lines.append(f"  By {col}:")
            for row in rows:
                value = row.get(col)
                labels = ", ".join(f"{k}={v}" for k, v in row.items() if k != col)
                lines.append(f"    {_fmt_num(value, money)} — {labels}")
    return "\n".join(lines)


async def get_ai_response(
    history: list[dict],
    data_contexts: list[dict] | None = None,
    rag_context: list[dict] | None = None,
) -> str:
    system_content = _BASE_SYSTEM_PROMPT
    if rag_context:
        system_content += "\n\n" + _format_rag_context(rag_context)
    if data_contexts:
        for ctx in data_contexts:
            system_content += "\n\n" + _format_data_context(ctx)

    messages = [{"role": "system", "content": system_content}] + history
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
    )
    return response.choices[0].message.content
