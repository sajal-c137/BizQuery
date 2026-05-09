"""Chart-friendly summaries for the visualization panel.

Returns a small set of pre-computed series the frontend can hand directly to
recharts. Respects the same field-level policy as the chat data proxy: PII /
identifier columns are skipped entirely; `internal` columns require admin.
"""
from pathlib import Path

import pandas as pd

from services.policy import classify

DATA_DIR = Path(__file__).parent.parent.parent / "database" / "data_sources"

_DATE_HINTS = ("date", "month")


def _is_visible(source_id: str, col: str, admin: bool) -> bool:
    sens = classify(source_id, col)
    if sens in ("pii", "identifier"):
        return False
    if sens == "internal" and not admin:
        return False
    return True


def _looks_like_date(col: str) -> bool:
    n = col.lower()
    return any(h in n for h in _DATE_HINTS)


_KPI_SKIP_HINTS = ("year", "rating", "minutes", "age", "_id")
_KPI_PREFER_HINTS = ("usd", "spend", "revenue", "budget", "impressions", "clicks",
                     "conversions", "subscribers", "votes", "hours")


def _kpi_score(name: str) -> int:
    n = name.lower()
    if any(h in n for h in _KPI_SKIP_HINTS):
        return -1
    return sum(1 for h in _KPI_PREFER_HINTS if h in n)


def _is_metric(col: str) -> bool:
    """Only columns that map to a recognized business measure are charted."""
    return _kpi_score(col) > 0


def _has_spread(values) -> bool:
    """Skip flat distributions — top slice must be visibly above the average."""
    vals = [abs(float(v)) for v in values if pd.notna(v)]
    if len(vals) < 2:
        return False
    total = sum(vals)
    if total <= 0:
        return False
    return max(vals) >= 1.5 * (total / len(vals))


def _kpis(df: pd.DataFrame, source_id: str, admin: bool) -> list[dict]:
    candidates = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and _is_visible(source_id, c, admin)
        and _is_metric(c)
    ]
    candidates.sort(key=lambda c: _kpi_score(c), reverse=True)
    out: list[dict] = []
    for col in candidates[:3]:
        out.append({
            "label": col.replace("_", " ").title(),
            "value": float(df[col].sum()),
            "kind": "money" if "usd" in col.lower() else "number",
        })
    return out


def _numeric_by_category_charts(df: pd.DataFrame, source_id: str, admin: bool) -> list[dict]:
    """For each business metric, sum it grouped by the most useful categorical."""
    charts: list[dict] = []
    cats = [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and not _looks_like_date(c)
        and _is_visible(source_id, c, admin)
        and 2 <= int(df[c].nunique()) <= 8
    ]
    if not cats:
        return charts
    pivot_cat = cats[0]
    metrics = [c for c in df.columns
               if pd.api.types.is_numeric_dtype(df[c])
               and _is_visible(source_id, c, admin)
               and _is_metric(c)
               and df[c].nunique() > 1]
    metrics.sort(key=_kpi_score, reverse=True)
    for col in metrics:
        grouped = df.groupby(pivot_cat)[col].sum().sort_values(ascending=False)
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
        if len(charts) >= 3:
            break
    return charts


def _time_series_charts(df: pd.DataFrame, source_id: str, admin: bool) -> list[dict]:
    """Plot business metrics over time only when there is real movement."""
    date_cols = [c for c in df.columns if _looks_like_date(c)]
    if not date_cols:
        return []
    date_col = date_cols[0]
    parsed = pd.to_datetime(df[date_col], errors="coerce")
    if parsed.isna().all():
        return []

    work = df.copy()
    work["_period"] = parsed.dt.to_period("M").astype(str)

    metrics = [c for c in df.columns
               if pd.api.types.is_numeric_dtype(df[c])
               and _is_visible(source_id, c, admin)
               and _is_metric(c)
               and df[c].nunique() > 1]
    metrics.sort(key=_kpi_score, reverse=True)

    charts: list[dict] = []
    for col in metrics:
        series = work.groupby("_period")[col].sum().sort_index()
        if len(series) < 3:
            continue
        mean = float(series.mean())
        if abs(mean) < 1e-9 or float(series.std()) / abs(mean) < 0.05:
            continue  # essentially flat
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
    path = DATA_DIR / f"{source_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Data source '{source_id}' not found")

    df = pd.read_csv(path)
    charts: list[dict] = []
    charts.extend(_time_series_charts(df, source_id, admin))
    charts.extend(_numeric_by_category_charts(df, source_id, admin))

    return {
        "source_id": source_id,
        "row_count": int(len(df)),
        "kpis": _kpis(df, source_id, admin),
        "charts": charts,
    }
