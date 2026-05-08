from pathlib import Path

import pandas as pd

from services.policy import classify, redact_context

DATA_DIR = Path(__file__).parent.parent.parent / "database" / "data_sources"


def list_sources() -> list[dict]:
    """Return all available CSV data sources."""
    return [
        {"id": f.stem, "name": f.stem.replace("_", " ").title()}
        for f in sorted(DATA_DIR.glob("*.csv"))
    ]


def get_data_context(source_id: str, admin: bool = False) -> dict:
    """Load a CSV source and return a structured context for the AI layer.

    The returned dict contains schema info, per-column statistics, and sample
    rows so the AI can answer analytical questions without seeing every row.
    """
    path = DATA_DIR / f"{source_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Data source '{source_id}' not found")

    df = pd.read_csv(path)

    columns = []
    for col in df.columns:
        col_info: dict = {"name": col, "dtype": str(df[col].dtype)}
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["stats"] = {
                "min": round(float(df[col].min()), 2),
                "max": round(float(df[col].max()), 2),
                "mean": round(float(df[col].mean()), 2),
                "sum": round(float(df[col].sum()), 2),
            }
        else:
            n_unique = int(df[col].nunique())
            col_info["unique_count"] = n_unique
            if n_unique <= 20:
                col_info["unique_values"] = sorted(df[col].dropna().astype(str).unique().tolist())
        columns.append(col_info)

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() <= 20
    ]

    group_stats = {}
    for cat in categorical_cols:
        grouped = df.groupby(cat)[numeric_cols].sum().round(2)
        group_stats[cat] = grouped.to_dict(orient="index")

    # Top-3 rows per numeric column, with public categorical labels only.
    # Lets the LLM answer "which movie had the biggest budget?" without
    # leaking row-level data through identifier or PII columns.
    public_label_cols = [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and classify(source_id, c) == "public"
    ]
    top_examples = {}
    for col in numeric_cols:
        if classify(source_id, col) in ("pii", "identifier"):
            continue
        if df[col].nunique() <= 1:
            continue
        rows = df.nlargest(3, col)[public_label_cols + [col]].to_dict(orient="records")
        top_examples[col] = rows

    return redact_context(source_id, {
        "source_id": source_id,
        "row_count": len(df),
        "columns": columns,
        "group_stats": group_stats,
        "top_examples": top_examples,
    }, admin=admin)
