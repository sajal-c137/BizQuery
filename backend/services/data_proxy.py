from pathlib import Path

import pandas as pd

from logger import get_logger
from services.policy import classify, redact_context

log = get_logger("data")

# data lives in repo-relative database/data_sources/
DATA_DIR = Path(__file__).parent.parent.parent / "database" / "data_sources"


def list_sources() -> list[dict]:
    # list all CSVs available — id is the filename stem
    if not DATA_DIR.exists():
        log.warning("data dir missing: %s", DATA_DIR)
        return []
    return [
        {"id": f.stem, "name": f.stem.replace("_", " ").title()}
        for f in sorted(DATA_DIR.glob("*.csv"))
    ]


def _load_csv(source_id: str) -> pd.DataFrame:
    # one place to load + verify a CSV
    path = DATA_DIR / f"{source_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Data source '{source_id}' not found")
    try:
        return pd.read_csv(path)
    except Exception as e:
        # corrupt CSV / encoding issue — surface as a 4xx-friendly error
        log.exception("failed to read %s", path)
        raise ValueError(f"Could not parse data source '{source_id}': {e}") from e


def get_data_context(source_id: str, admin: bool = False) -> dict:
    # build a structured summary of a CSV for the AI layer
    # never returns raw rows — only schema + aggregates + a few public top rows
    df = _load_csv(source_id)
    log.info("building context for %s (%d rows)", source_id, len(df))

    # walk columns, classify each by dtype
    columns = []
    for col in df.columns:
        col_info: dict = {"name": col, "dtype": str(df[col].dtype)}
        if pd.api.types.is_numeric_dtype(df[col]):
            # numeric — emit summary stats
            try:
                col_info["stats"] = {
                    "min": round(float(df[col].min()), 2),
                    "max": round(float(df[col].max()), 2),
                    "mean": round(float(df[col].mean()), 2),
                    "sum": round(float(df[col].sum()), 2),
                }
            except Exception:
                # all-NaN column or similar — skip stats
                log.warning("could not compute stats for %s.%s", source_id, col)
        else:
            # categorical — emit unique count and a few values if low-cardinality
            n_unique = int(df[col].nunique())
            col_info["unique_count"] = n_unique
            if n_unique <= 20:
                col_info["unique_values"] = sorted(
                    df[col].dropna().astype(str).unique().tolist()
                )
        columns.append(col_info)

    # used both for grouping and for "top rows" labels
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() <= 20
    ]

    # group totals — sums of every numeric col by every low-card categorical
    group_stats: dict[str, dict] = {}
    for cat in categorical_cols:
        try:
            grouped = df.groupby(cat)[numeric_cols].sum().round(2)
            group_stats[cat] = grouped.to_dict(orient="index")
        except Exception:
            # uncommon dtypes / NaN cats — skip
            log.warning("groupby failed on %s.%s", source_id, cat)

    # top-3 rows per numeric col, with PUBLIC categorical labels only
    # answers "which movie had the biggest budget?" without leaking ids/PII
    public_label_cols = [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and classify(source_id, c) == "public"
    ]
    top_examples: dict[str, list] = {}
    for col in numeric_cols:
        if classify(source_id, col) in ("pii", "identifier"):
            continue
        # constant column — nothing interesting to surface
        if df[col].nunique() <= 1:
            continue
        try:
            rows = df.nlargest(3, col)[public_label_cols + [col]].to_dict(orient="records")
            top_examples[col] = rows
        except Exception:
            log.warning("nlargest failed on %s.%s", source_id, col)

    # apply field-level policy (drop internal cols if not admin, redact PII)
    return redact_context(source_id, {
        "source_id": source_id,
        "row_count": len(df),
        "columns": columns,
        "group_stats": group_stats,
        "top_examples": top_examples,
    }, admin=admin)
