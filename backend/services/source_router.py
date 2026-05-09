"""LLM-based router that picks which CSV data sources a question needs."""
import json

import pandas as pd

from config import settings
from logger import get_logger
from services.data_proxy import DATA_DIR, list_sources
from services.openai_client import client

log = get_logger("router")

# small system prompt — strict JSON output
_ROUTER_SYSTEM = (
    "You are a data routing assistant. Given a user's question and a list of "
    "available data sources with their columns, return ONLY the source ids that "
    "are needed to answer the question. Pick zero, one, or multiple sources. "
    'Reply with JSON only: {"sources": ["id1", "id2"]}.'
)


def _schema_summary() -> str:
    # one-line-per-source schema list to feed the router prompt
    lines = []
    for s in list_sources():
        try:
            cols = pd.read_csv(DATA_DIR / f"{s['id']}.csv", nrows=0).columns.tolist()
            lines.append(f"- {s['id']}: {', '.join(cols)}")
        except Exception:
            # skip sources we can't read — log but don't fail routing
            log.warning("could not read schema for %s", s["id"])
    return "\n".join(lines)


async def route_sources(question: str) -> list[str]:
    # ask the LLM which CSVs are relevant for this question
    valid_ids = {s["id"] for s in list_sources()}
    if not valid_ids:
        # nothing to route to
        return []

    user_content = (
        f"Available data sources:\n{_schema_summary()}\n\n"
        f"Question: {question}"
    )

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _ROUTER_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        # routing is best-effort: fall back to "no sources" rather than crashing
        log.exception("source router LLM call failed")
        return []

    raw = (response.choices[0].message.content or "") if response.choices else ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("router returned non-JSON: %r", raw[:200])
        return []

    picked = parsed.get("sources") if isinstance(parsed, dict) else None
    if not isinstance(picked, list):
        return []

    # filter out anything the model hallucinated
    valid = [s for s in picked if isinstance(s, str) and s in valid_ids]
    log.info("router picked %d/%d sources for question", len(valid), len(picked))
    return valid
