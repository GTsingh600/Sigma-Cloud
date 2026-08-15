"""
Shared dataset construction helpers.

Used by both the upload path and the database-import path so a dataset created
from a SQL table is indistinguishable downstream from an uploaded CSV.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def safe_storage_filename(original_name: str, user_id: int, prefix: str = "") -> str:
    """Build a collision-free, traversal-proof storage filename.

    `os.path.basename` strips any directory component a crafted multipart
    filename might carry, then the remainder is reduced to a known-safe
    character set - `os.path.join` would otherwise happily honour '../'.
    """
    base = os.path.basename(original_name or "dataset.csv")
    base = _UNSAFE_FILENAME_CHARS.sub("_", base).strip("._") or "dataset.csv"
    base = base[-120:]
    unique = uuid.uuid4().hex[:8]
    parts = [f"user_{user_id}", prefix, unique, base]
    return "_".join(part for part in parts if part)


def analyze_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Per-column metadata shown in dataset previews."""
    columns_info: List[Dict[str, Any]] = []

    for col in df.columns:
        col_data = df[col]
        info: Dict[str, Any] = {
            "name": str(col),
            "dtype": str(col_data.dtype),
            "null_count": int(col_data.isnull().sum()),
            "unique_count": int(col_data.nunique()),
            "sample_values": _json_safe_list(col_data.dropna().head(5).tolist()),
        }

        if pd.api.types.is_numeric_dtype(col_data) and not pd.api.types.is_bool_dtype(col_data):
            non_null = col_data.dropna()
            if not non_null.empty:
                info["stats"] = {
                    "min": float(non_null.min()),
                    "max": float(non_null.max()),
                    "mean": float(non_null.mean()),
                    "std": float(non_null.std()) if len(non_null) > 1 else 0.0,
                    "median": float(non_null.median()),
                }

        columns_info.append(info)

    return columns_info


def _json_safe_list(values: List[Any]) -> List[Any]:
    safe: List[Any] = []
    for value in values:
        if value is None or isinstance(value, (int, float, str, bool)):
            safe.append(value)
        else:
            safe.append(str(value))
    return safe


def build_preview(df: pd.DataFrame, rows: int = 10) -> List[Dict[str, Any]]:
    preview = df.head(rows).copy()
    for column in preview.columns:
        preview[column] = preview[column].map(
            lambda value: value
            if value is None or isinstance(value, (int, float, str, bool))
            else str(value)
        )
    return preview.where(pd.notna(preview), "").to_dict(orient="records")


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """SQL results can carry duplicate or unnamed columns; make them unique."""
    seen: Dict[str, int] = {}
    renamed = []

    for index, column in enumerate(df.columns):
        name = str(column).strip() or f"column_{index + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        renamed.append(name)

    df.columns = renamed
    return df


def persist_dataframe(
    df: pd.DataFrame,
    user_id: int,
    filename: str,
    prefix: str = "",
) -> Dict[str, Any]:
    """Write a DataFrame to dataset storage and return file metadata."""
    os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)
    stored_name = safe_storage_filename(filename, user_id, prefix)
    file_path = os.path.join(settings.DATASET_STORAGE_PATH, stored_name)

    df.to_csv(file_path, index=False)

    return {
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "num_rows": int(len(df)),
        "num_columns": int(len(df.columns)),
        "columns_info": analyze_dataframe(df),
        "preview_data": build_preview(df),
    }


def dataset_file_exists(file_path: Optional[str]) -> bool:
    return bool(file_path) and os.path.exists(file_path)
