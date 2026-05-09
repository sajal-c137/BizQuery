"""Field-level data classification + redaction.

Policy levels:
  public      - no restriction
  internal    - confidential metric; aggregates allowed for admins only
  pii         - personal data; values redacted, never used as a group key
  identifier  - opaque key (movie_id, viewer_id, ...); always redacted
"""
from typing import Literal

Sensitivity = Literal["public", "internal", "pii", "identifier"]

# (source_id, column) -> sensitivity
# anything not listed defaults to "public"
# keep "internal" narrow — only the most commercially sensitive fields
# operational metrics (subs, impressions, clicks) stay public so the
# assistant has plenty to talk about without admin mode
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
        # production budgets are confidential
        "budget_usd": "internal",
    },
    "marketing_spend": {
        # competitive intel
        "spend_usd": "internal",
    },
    "regional_performance": {
        # regional revenue breakdown is confidential
        "revenue_usd": "internal",
    },
    "title_campaigns": {
        "movie_id":           "identifier",
        # per-title spend is competitive intel
        "campaign_spend_usd": "internal",
    },
}


def classify(source_id: str, column: str) -> Sensitivity:
    # default to public when nothing's listed
    return COLUMN_POLICY.get(source_id, {}).get(column, "public")


def redact_context(source_id: str, ctx: dict, admin: bool = False) -> dict:
    # apply field-level policy:
    #   - admin=False -> drop "internal" columns entirely
    #   - admin=True  -> keep internal cols, mark them as confidential
    # PII / identifier values are always stripped, regardless of admin.

    # which numeric cols should disappear from the prompt
    hidden_internal = {
        col["name"]
        for col in ctx["columns"]
        if classify(source_id, col["name"]) == "internal" and not admin
    }

    # rewrite the columns list — drop hidden, tag the rest
    redacted_columns = []
    for col in ctx["columns"]:
        if col["name"] in hidden_internal:
            continue
        sens = classify(source_id, col["name"])
        col = {**col, "sensitivity": sens}
        # never enumerate PII/identifier values
        if sens in ("pii", "identifier"):
            col.pop("unique_values", None)
        redacted_columns.append(col)

    # group stats: drop entire group keys that are PII/identifier or hidden
    redacted_groups: dict[str, dict] = {}
    for cat, groups in ctx.get("group_stats", {}).items():
        cat_sens = classify(source_id, cat)
        if cat_sens in ("pii", "identifier"):
            continue
        if cat_sens == "internal" and not admin:
            continue
        # also strip hidden numeric cols out of the per-group stats
        redacted_groups[cat] = {
            grp_val: {k: v for k, v in stats.items() if k not in hidden_internal}
            for grp_val, stats in groups.items()
        }

    # top examples — drop hidden / sensitive metrics
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
