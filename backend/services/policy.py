"""Field-level data classification + redaction for the data proxy layer.

Policy levels
-------------
public      - no restriction (most categorical fields)
internal    - confidential business metric; aggregates allowed, mark in prompt
pii         - personal/quasi-identifier; values redacted, group keys dropped
identifier  - opaque key (movie_id, viewer_id, ...); values redacted

The proxy already emits only aggregates (never row-level data), so this layer
controls what *aggregate* shape is allowed: which categorical values are
enumerated, which columns can be group-by keys, and how each column is tagged
in the LLM prompt.
"""
from typing import Literal

Sensitivity = Literal["public", "internal", "pii", "identifier"]

# (source_id, column) -> sensitivity. Anything missing defaults to "public".
# Keep "internal" narrow: only the most commercially sensitive financials.
# Operational metrics (subs, impressions, clicks, watch hours) stay public so
# the assistant has plenty to discuss without admin mode enabled.
COLUMN_POLICY: dict[str, dict[str, Sensitivity]] = {
    "viewers": {
        "viewer_id": "identifier",
        "age":       "pii",
        "join_date": "pii",
    },
    "watch_activity": {
        "activity_id": "identifier",
        "viewer_id":   "identifier",
        "movie_id":    "identifier",
        "watch_date":  "pii",
    },
    "reviews": {
        "review_id":   "identifier",
        "viewer_id":   "identifier",
        "movie_id":    "identifier",
        "review_date": "pii",
    },
    "movies": {
        "movie_id":   "identifier",
        "budget_usd": "internal",   # production budgets are confidential
    },
    "marketing_spend": {
        "spend_usd": "internal",    # competitive intel
    },
    "regional_performance": {
        "revenue_usd": "internal",  # regional revenue breakdown is confidential
    },
    "title_campaigns": {
        "movie_id":           "identifier",
        "campaign_spend_usd": "internal",  # per-title spend is competitive intel
    },
}


def classify(source_id: str, column: str) -> Sensitivity:
    return COLUMN_POLICY.get(source_id, {}).get(column, "public")


def redact_context(source_id: str, ctx: dict, admin: bool = False) -> dict:
    """Apply field-level policy: tag every column, drop sensitive enumerations.

    admin=False (default): drop "internal" columns entirely (the LLM never sees them).
    admin=True:            keep "internal" columns, mark them confidential in the prompt.
    PII / identifier columns are always redacted regardless of admin mode.
    """
    hidden_internal = {
        col["name"]
        for col in ctx["columns"]
        if classify(source_id, col["name"]) == "internal" and not admin
    }

    redacted_columns = []
    for col in ctx["columns"]:
        if col["name"] in hidden_internal:
            continue
        sens = classify(source_id, col["name"])
        col = {**col, "sensitivity": sens}
        if sens in ("pii", "identifier"):
            col.pop("unique_values", None)
        redacted_columns.append(col)

    redacted_groups = {}
    for cat, groups in ctx.get("group_stats", {}).items():
        cat_sens = classify(source_id, cat)
        if cat_sens in ("pii", "identifier"):
            continue
        if cat_sens == "internal" and not admin:
            continue
        # Strip hidden internal numeric columns from per-group stats.
        redacted_groups[cat] = {
            grp_val: {k: v for k, v in stats.items() if k not in hidden_internal}
            for grp_val, stats in groups.items()
        }

    redacted_top = {
        col: rows
        for col, rows in ctx.get("top_examples", {}).items()
        if col not in hidden_internal
        and classify(source_id, col) not in ("pii", "identifier")
    }

    return {
        **ctx,
        "columns": redacted_columns,
        "group_stats": redacted_groups,
        "top_examples": redacted_top,
        "admin": admin,
    }
