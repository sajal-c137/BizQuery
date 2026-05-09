"""Chart-friendly summaries for the visualization panel.

Returns a small set of pre-computed series the frontend hands directly to
recharts. Same field-level policy as the chat data proxy applies: PII /
identifier columns are skipped, `internal` columns require admin.
"""
from pathlib import Path

import pandas as pd

from logger import get_logger
from services.policy import classify

log = get_logger("charts")

# CSVs live alongside the data proxy
DATA_DIR = Path(__file__).parent.parent.parent / "database" / "data_sources"

# substrings that hint a column is a time axis
_DATE_HINTS = ("date", "month")

# substrings that mean a numeric column is NOT a business metric
_KPI_SKIP_HINTS = ("year", "rating", "minutes", "age", "_id")
# substrings that DO mark a column as a business metric
_KPI_PREFER_HINTS = (
    "usd", "spend", "revenue", "budget", "impressions", "clicks",
    "conversions", "subscribers", "votes", "hours",
)


def _is_visible(source_id: str, col: str, admin: bool) -> bool:
    # respect the same policy as the chat proxy
    sens = classify(source_id, col)
    if sens in ("pii", "identifier"):
        return False
    if sens == "internal" and not admin:
        return False
    return True


def _looks_like_date(col: str) -> bool:
    # tolerant — any "date"/"month" substring counts
    n = col.lower()
    return any(h in n for h in _DATE_HINTS)


def _kpi_score(name: str) -> int:
    # score >0 = business metric, -1 = skip
    n = name.lower()
    if any(h in n for h in _KPI_SKIP_HINTS):
        return -1
    return sum(1 for h in _KPI_PREFER_HINTS if h in n)


def _is_metric(col: str) -> bool:
    # only chart cols that look like real KPIs
    return _kpi_score(col) > 0


def _has_spread(values) -> bool:
    # filter out flat distributions (top slice not visibly above the average)
    vals = [abs(float(v)) for v in values if pd.notna(v)]
    if len(vals) < 2:
        return False
    total = sum(vals)
    if total <= 0:
        return False
    return max(vals) >= 1.5 * (total / len(vals))


def _kpis(df: pd.DataFrame, source_id: str, admin: bool) -> list[dict]:
    # top 3 metric columns -> KPI cards
    candidates = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and _is_visible(source_id, c, admin)
        and _is_metric(c)
    ]
    candidates.sort(key=_kpi_score, reverse=True)
    out: list[dict] = []
    for col in candidates[:3]:
        try:
            out.append({
                "label": col.replace("_", " ").title(),
                "value": float(df[col].sum()),
                "kind": "money" if "usd" in col.lower() else "number",
            })
        except Exception:
            log.warning("KPI sum failed on %s.%s", source_id, col)
    return out


def _numeric_by_category_charts(df: pd.DataFrame, source_id: str, admin: bool) -> list[dict]:
    # for each metric, sum it grouped by the most useful categorical
    charts: list[dict] = []

    # pick candidate categorical (low-card, not date, visible)
    cats = [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and not _looks_like_date(c)
        and _is_visible(source_id, c, admin)
        and 2 <= int(df[c].nunique()) <= 8
    ]
    if not cats:
        return charts

    # use the first low-card categorical as the pivot
    pivot_cat = cats[0]

    # candidate metrics — drop constants and policy-restricted
    metrics = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and _is_visible(source_id, c, admin)
        and _is_metric(c)
        and df[c].nunique() > 1
    ]
    metrics.sort(key=_kpi_score, reverse=True)

    for col in metrics:
        try:
            grouped = df.groupby(pivot_cat)[col].sum().sort_values(ascending=False)
        except Exception:
            log.warning("groupby failed for %s.%s", source_id, col)
            continue
        # skip flat-looking series
        if not _has_spread(grouped.values):
            continue
        charts.append({
            "type": "bar",
            "title": f"{col.replace('_', ' ').title()} by {pivot_cat.title()}",
            "x_label": pivot_cat,
            "y_label": col,
            "money": "usd" in col.lower(),
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in grouped.items()],
        })
        # cap at 3 charts per category
        if len(charts) >= 3:
            break
    return charts


def _time_series_charts(df: pd.DataFrame, source_id: str, admin: bool) -> list[dict]:
    # plot metrics over time when there's real movement
    date_cols = [c for c in df.columns if _looks_like_date(c)]
    if not date_cols:
        return []

    date_col = date_cols[0]
    parsed = pd.to_datetime(df[date_col], errors="coerce")
    if parsed.isna().all():
        # not actually parseable as dates — bail
        return []

    work = df.copy()
    work["_period"] = parsed.dt.to_period("M").astype(str)

    # candidate metrics (same gates as bar charts)
    metrics = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and _is_visible(source_id, c, admin)
        and _is_metric(c)
        and df[c].nunique() > 1
    ]
    metrics.sort(key=_kpi_score, reverse=True)

    charts: list[dict] = []
    for col in metrics:
        try:
            series = work.groupby("_period")[col].sum().sort_index()
        except Exception:
            log.warning("time-series groupby failed for %s.%s", source_id, col)
            continue

        # need at least a few points to be meaningful
        if len(series) < 3:
            continue
        mean = float(series.mean())
        # essentially flat? skip
        if abs(mean) < 1e-9 or float(series.std()) / abs(mean) < 0.05:
            continue

        charts.append({
            "type": "line",
            "title": f"{col.replace('_', ' ').title()} over Time",
            "x_label": "month",
            "y_label": col,
            "money": "usd" in col.lower(),
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in series.items()],
        })
        if len(charts) >= 3:
            break
    return charts


def get_chart_bundle(source_id: str, admin: bool = False) -> dict:
    # entry point for the visualization panel
    path = DATA_DIR / f"{source_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Data source '{source_id}' not found")

    try:
        df = pd.read_csv(path)
    except Exception as e:
        log.exception("failed to read CSV: %s", path)
        raise ValueError(f"Could not parse data source '{source_id}': {e}") from e

    # build chart list — time series first, then by-category
    charts: list[dict] = []
    charts.extend(_time_series_charts(df, source_id, admin))
    charts.extend(_numeric_by_category_charts(df, source_id, admin))

    log.info("chart bundle for %s: %d KPIs, %d charts", source_id, 0, len(charts))

    return {
        "source_id": source_id,
        "row_count": int(len(df)),
        "kpis": _kpis(df, source_id, admin),
        "charts": charts,
    }
