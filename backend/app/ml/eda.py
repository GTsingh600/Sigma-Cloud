"""
Dataset-specific EDA generation utilities.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_categorical_dtype,
    is_numeric_dtype,
    is_object_dtype,
)


MAX_ANALYSIS_ROWS = 5000
MAX_TOP_ITEMS = 8
MAX_NUMERIC_VISUALS = 3
MAX_CATEGORICAL_VISUALS = 3
MAX_CORRELATION_FEATURES = 6


def load_dataset_dataframe(file_path: str) -> pd.DataFrame:
    if file_path.endswith(".csv"):
        return pd.read_csv(file_path)
    return pd.read_excel(file_path)


def generate_dataset_analysis(df: pd.DataFrame, target_column: str | None = None) -> Dict[str, Any]:
    sampled_df = _sample_dataframe(df)
    numeric_columns, categorical_columns = _classify_columns(sampled_df, target_column)

    summary = _build_summary(df, sampled_df, numeric_columns, categorical_columns, target_column)
    insights = _build_insights(sampled_df, numeric_columns, categorical_columns, target_column)
    visualizations = _build_visualizations(sampled_df, numeric_columns, categorical_columns, target_column)

    return {
        "summary": summary,
        "insights": insights,
        "visualizations": visualizations,
    }


def _sample_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= MAX_ANALYSIS_ROWS:
        return df.copy()
    return df.sample(MAX_ANALYSIS_ROWS, random_state=42).copy()


def _classify_columns(df: pd.DataFrame, target_column: str | None) -> Tuple[List[str], List[str]]:
    numeric_columns: List[str] = []
    categorical_columns: List[str] = []

    for column in df.columns:
        series = df[column]
        non_null = series.dropna()
        unique_count = int(non_null.nunique())
        unique_ratio = unique_count / max(len(non_null), 1)

        if is_bool_dtype(series) or is_object_dtype(series) or is_categorical_dtype(series):
            categorical_columns.append(column)
            continue

        if is_numeric_dtype(series):
            if column != target_column and unique_count <= 12 and unique_ratio <= 0.05:
                categorical_columns.append(column)
            else:
                numeric_columns.append(column)
            continue

        categorical_columns.append(column)

    return numeric_columns, categorical_columns


def _build_summary(
    df: pd.DataFrame,
    sampled_df: pd.DataFrame,
    numeric_columns: List[str],
    categorical_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any]:
    missing_cells = int(df.isna().sum().sum())
    total_cells = int(max(df.shape[0] * max(df.shape[1], 1), 1))

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "sampled_rows": int(sampled_df.shape[0]),
        "numeric_columns": len(numeric_columns),
        "categorical_columns": len(categorical_columns),
        "missing_cells": missing_cells,
        "missing_pct": round((missing_cells / total_cells) * 100, 2),
        "target_column": target_column,
    }


def _build_insights(
    df: pd.DataFrame,
    numeric_columns: List[str],
    categorical_columns: List[str],
    target_column: str | None,
) -> List[str]:
    insights: List[str] = []
    missing_pct = (df.isna().sum().sum() / max(df.shape[0] * max(df.shape[1], 1), 1)) * 100
    if missing_pct > 0:
        worst = df.isna().mean().sort_values(ascending=False)
        worst_column = worst.index[0]
        insights.append(f"Missing data is concentrated in '{worst_column}' ({worst.iloc[0] * 100:.1f}%).")

    duplicate_ratio = float(df.duplicated().mean()) if len(df) > 0 else 0.0
    if duplicate_ratio >= 0.03:
        insights.append(f"{duplicate_ratio * 100:.1f}% of sampled rows are duplicates, which can bias evaluation.")

    constant_columns = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]
    if constant_columns:
        insights.append(f"{len(constant_columns)} column(s) are constant and add little signal.")

    if target_column and target_column in df.columns:
        target = df[target_column]
        if target_column in numeric_columns:
            correlations = (
                df[numeric_columns]
                .corr(numeric_only=True)[target_column]
                .drop(labels=[target_column], errors="ignore")
                .dropna()
            )
            if not correlations.empty:
                best = correlations.abs().sort_values(ascending=False).index[0]
                insights.append(
                    f"'{best}' has the strongest linear relationship with target '{target_column}' "
                    f"({correlations[best]:.2f})."
                )
        else:
            target_counts = target.fillna("(Missing)").astype(str).value_counts(normalize=True)
            if not target_counts.empty and target_counts.iloc[0] > 0.7:
                insights.append(
                    f"Target '{target_column}' is imbalanced; '{target_counts.index[0]}' makes up "
                    f"{target_counts.iloc[0] * 100:.1f}% of rows."
                )
            elif not target_counts.empty:
                effective_classes = int((target_counts > 0.05).sum())
                insights.append(f"Target '{target_column}' has {effective_classes} materially represented classes.")

    skewed_columns = []
    for column in numeric_columns:
        clean = pd.to_numeric(df[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(clean) > 10:
            skew = clean.skew()
            if pd.notna(skew) and abs(float(skew)) >= 1.0:
                skewed_columns.append((column, abs(float(skew))))
    skewed_columns.sort(key=lambda item: item[1], reverse=True)
    if skewed_columns:
        insights.append(f"'{skewed_columns[0][0]}' is strongly skewed and may benefit from transformation.")

    high_cardinality = [
        column for column in categorical_columns
        if df[column].nunique(dropna=True) > min(25, max(int(len(df) * 0.1), 10))
    ]
    if high_cardinality:
        insights.append(f"'{high_cardinality[0]}' has high cardinality and may need grouping or encoding care.")

    if len(numeric_columns) >= 2:
        corr = df[numeric_columns].corr(numeric_only=True).abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        stacked = upper.stack().sort_values(ascending=False)
        if not stacked.empty and stacked.iloc[0] >= 0.85:
            left, right = stacked.index[0]
            insights.append(
                f"'{left}' and '{right}' are highly correlated ({stacked.iloc[0]:.2f}), which may indicate redundancy."
            )

    wide_ratio = len(df.columns) / max(len(df), 1)
    if wide_ratio >= 0.2:
        insights.append("This dataset is relatively wide; feature selection or regularization will matter.")

    deduped: List[str] = []
    seen = set()
    for insight in insights:
        if insight not in seen:
            deduped.append(insight)
            seen.add(insight)
    return deduped[:8]


def _build_visualizations(
    df: pd.DataFrame,
    numeric_columns: List[str],
    categorical_columns: List[str],
    target_column: str | None,
) -> List[Dict[str, Any]]:
    visualizations: List[Dict[str, Any]] = []

    missing_chart = _build_missing_visual(df)
    if missing_chart:
        visualizations.append(missing_chart)

    target_chart = _build_target_visual(df, numeric_columns, target_column)
    if target_chart:
        visualizations.append(target_chart)

    target_relationship_chart = _build_target_relationship_visual(df, numeric_columns, target_column)
    if target_relationship_chart:
        visualizations.append(target_relationship_chart)

    for chart in _build_numeric_distribution_visuals(df, numeric_columns, target_column):
        visualizations.append(chart)

    for chart in _build_categorical_distribution_visuals(df, categorical_columns, target_column):
        visualizations.append(chart)

    box_summary_chart = _build_box_summary_visual(df, numeric_columns, target_column)
    if box_summary_chart:
        visualizations.append(box_summary_chart)

    scatter_chart = _build_scatter_visual(df, numeric_columns, target_column)
    if scatter_chart:
        visualizations.append(scatter_chart)

    category_target_chart = _build_categorical_target_visual(df, categorical_columns, target_column)
    if category_target_chart:
        visualizations.append(category_target_chart)

    correlation_chart = _build_correlation_visual(df, numeric_columns, target_column)
    if correlation_chart:
        visualizations.append(correlation_chart)

    return visualizations


def _build_missing_visual(df: pd.DataFrame) -> Dict[str, Any] | None:
    missing = df.isna().mean()
    missing = missing[missing > 0].sort_values(ascending=False).head(MAX_TOP_ITEMS)
    if missing.empty:
        return None

    data = [
        {
            "column": column,
            "missing_pct": round(float(value * 100), 2),
            "missing_count": int(df[column].isna().sum()),
        }
        for column, value in missing.items()
    ]

    return {
        "id": "missing-values",
        "title": "Missing Value Pressure",
        "description": "Highlights where data quality is most likely to distort analysis or training.",
        "chart_type": "bar",
        "x_key": "column",
        "series": [{"key": "missing_pct", "label": "Missing %"}],
        "data": data,
        "value_format": "percent",
    }


def _build_target_visual(
    df: pd.DataFrame,
    numeric_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any] | None:
    if not target_column or target_column not in df.columns:
        return None

    if target_column in numeric_columns:
        data = _histogram_data(df[target_column])
        if not data:
            return None
        return {
            "id": "target-distribution",
            "title": f"Target Distribution: {target_column}",
            "description": "Shows how the prediction target is spread across the dataset.",
            "chart_type": "histogram",
            "x_key": "bucket",
            "series": [{"key": "count", "label": "Rows"}],
            "data": data,
            "value_format": "count",
        }

    data = _top_counts_data(df[target_column])
    if not data:
        return None

    return {
        "id": "target-distribution",
        "title": f"Target Balance: {target_column}",
        "description": "Class balance matters for training quality and evaluation strategy.",
        "chart_type": "bar",
        "x_key": "label",
        "series": [{"key": "count", "label": "Rows"}],
        "data": data,
        "value_format": "count",
    }


def _build_target_relationship_visual(
    df: pd.DataFrame,
    numeric_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any] | None:
    if not target_column or target_column not in df.columns:
        return None

    if target_column in numeric_columns:
        candidates = [column for column in numeric_columns if column != target_column]
        if not candidates:
            return None

        correlations = (
            df[candidates + [target_column]]
            .corr(numeric_only=True)[target_column]
            .drop(labels=[target_column], errors="ignore")
            .dropna()
        )
        if correlations.empty:
            return None

        top = correlations.reindex(correlations.abs().sort_values(ascending=False).index).head(MAX_TOP_ITEMS)
        data = [
            {"feature": column, "correlation": round(float(value), 3)}
            for column, value in top.items()
        ]
        return {
            "id": "target-correlations",
            "title": f"Strongest Drivers of {target_column}",
            "description": "Focuses on numeric features with the clearest linear relationship to the target.",
            "chart_type": "bar",
            "x_key": "feature",
            "series": [{"key": "correlation", "label": "Correlation"}],
            "data": data,
            "value_format": "number",
        }

    candidate_numeric = [column for column in numeric_columns if column != target_column]
    if not candidate_numeric:
        return None

    target_series = df[target_column].fillna("(Missing)").astype(str)
    target_levels = target_series.value_counts().head(6).index.tolist()
    filtered = df[target_series.isin(target_levels)].copy()
    filtered_target = filtered[target_column].fillna("(Missing)").astype(str)

    scored_features: List[Tuple[str, float]] = []
    for column in candidate_numeric:
        clean = pd.to_numeric(filtered[column], errors="coerce")
        merged = pd.DataFrame({"target": filtered_target, "value": clean}).dropna()
        if merged.empty or merged["target"].nunique() < 2:
            continue
        total_var = float(merged["value"].var())
        if total_var <= 0:
            continue
        grouped = merged.groupby("target")["value"]
        means = grouped.mean()
        counts = grouped.size()
        overall_mean = float(merged["value"].mean())
        between = float((((means - overall_mean) ** 2) * counts).sum() / max(len(merged), 1))
        scored_features.append((column, between / total_var))

    scored_features.sort(key=lambda item: item[1], reverse=True)
    top_features = [feature for feature, _ in scored_features[:4]]
    if not top_features:
        return None

    grouped_means = (
        filtered.assign(_target=filtered_target)
        .groupby("_target")[top_features]
        .mean(numeric_only=True)
        .reset_index()
    )
    data = []
    for _, row in grouped_means.iterrows():
        item = {"label": _to_label(row["_target"])}
        for feature in top_features:
            item[feature] = round(_to_float(row[feature]), 3)
        data.append(item)

    return {
        "id": "target-class-profile",
        "title": f"How Classes Differ on Key Numeric Features",
        "description": f"Compares class-level averages against target '{target_column}' to surface discriminating features.",
        "chart_type": "grouped_bar",
        "x_key": "label",
        "series": [{"key": feature, "label": feature} for feature in top_features],
        "data": data,
        "value_format": "number",
    }


def _build_numeric_distribution_visuals(
    df: pd.DataFrame,
    numeric_columns: List[str],
    target_column: str | None,
) -> List[Dict[str, Any]]:
    candidates = [column for column in numeric_columns if column != target_column]
    scored = sorted(
        (
            (
                column,
                _numeric_priority_score(df[column], target=df[target_column] if target_column in df.columns else None),
            )
            for column in candidates
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    visualizations: List[Dict[str, Any]] = []
    for column, _ in scored[:MAX_NUMERIC_VISUALS]:
        data = _histogram_data(df[column])
        if not data:
            continue
        visualizations.append(
            {
                "id": f"numeric-distribution-{column}",
                "title": f"Distribution of {column}",
                "description": "Selected because it carries strong spread, skew, or target signal.",
                "chart_type": "histogram",
                "x_key": "bucket",
                "series": [{"key": "count", "label": "Rows"}],
                "data": data,
                "value_format": "count",
            }
        )

    return visualizations


def _build_categorical_distribution_visuals(
    df: pd.DataFrame,
    categorical_columns: List[str],
    target_column: str | None,
) -> List[Dict[str, Any]]:
    candidates = [column for column in categorical_columns if column != target_column]
    scored = sorted(
        ((column, _categorical_priority_score(df[column])) for column in candidates),
        key=lambda item: item[1],
        reverse=True,
    )

    visualizations: List[Dict[str, Any]] = []
    for column, _ in scored[:MAX_CATEGORICAL_VISUALS]:
        data = _top_counts_data(df[column])
        if not data:
            continue
        visualizations.append(
            {
                "id": f"categorical-distribution-{column}",
                "title": f"Composition of {column}",
                "description": "Selected because category balance or concentration is likely to matter for this dataset.",
                "chart_type": "bar",
                "x_key": "label",
                "series": [{"key": "count", "label": "Rows"}],
                "data": data,
                "value_format": "count",
            }
        )

    return visualizations


def _build_correlation_visual(
    df: pd.DataFrame,
    numeric_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any] | None:
    candidates = [column for column in numeric_columns if column != target_column]
    if len(candidates) < 3:
        return None

    scored = sorted(
        (
            (
                column,
                _numeric_priority_score(df[column], target=df[target_column] if target_column in df.columns else None),
            )
            for column in candidates
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    top_columns = [column for column, _ in scored[:MAX_CORRELATION_FEATURES]]
    corr = df[top_columns].corr(numeric_only=True).round(3)
    if corr.empty:
        return None

    data = []
    for row in corr.index:
        for column in corr.columns:
            value = corr.loc[row, column]
            if pd.isna(value):
                continue
            data.append({"row": row, "column": column, "value": float(value)})

    return {
        "id": "correlation-heatmap",
        "title": "Feature Correlation Map",
        "description": "Surfaces redundant features and tightly linked numeric signals.",
        "chart_type": "heatmap",
        "data": data,
        "value_format": "correlation",
    }


def _build_box_summary_visual(
    df: pd.DataFrame,
    numeric_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any] | None:
    candidates = [column for column in numeric_columns if column != target_column]
    if not candidates:
        return None

    scored = sorted(
        (
            (
                column,
                _numeric_priority_score(df[column], target=df[target_column] if target_column in df.columns else None),
            )
            for column in candidates
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    data = []
    for column, _ in scored[:4]:
        clean = pd.to_numeric(df[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(clean) < 5:
            continue
        quantiles = clean.quantile([0.0, 0.25, 0.5, 0.75, 1.0])
        data.append(
            {
                "feature": column,
                "min": round(float(quantiles.loc[0.0]), 3),
                "q1": round(float(quantiles.loc[0.25]), 3),
                "median": round(float(quantiles.loc[0.5]), 3),
                "q3": round(float(quantiles.loc[0.75]), 3),
                "max": round(float(quantiles.loc[1.0]), 3),
            }
        )

    if not data:
        return None

    return {
        "id": "box-summary",
        "title": "Spread and Outlier Risk",
        "description": "Quartile summaries for the most structurally important numeric features.",
        "chart_type": "box_summary",
        "x_key": "feature",
        "data": data,
        "value_format": "number",
    }


def _build_scatter_visual(
    df: pd.DataFrame,
    numeric_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any] | None:
    if target_column and target_column in numeric_columns:
        candidates = [column for column in numeric_columns if column != target_column]
        if not candidates:
            return None
        correlations = (
            df[candidates + [target_column]]
            .corr(numeric_only=True)[target_column]
            .drop(labels=[target_column], errors="ignore")
            .dropna()
        )
        if correlations.empty:
            return None
        x_feature = correlations.abs().sort_values(ascending=False).index[0]
        sample = pd.DataFrame({
            "x": pd.to_numeric(df[x_feature], errors="coerce"),
            "y": pd.to_numeric(df[target_column], errors="coerce"),
        }).dropna()
        if sample.empty:
            return None
        if len(sample) > 500:
            sample = sample.sample(500, random_state=42)
        data = [{"x": round(float(row.x), 3), "y": round(float(row.y), 3)} for row in sample.itertuples()]
        return {
            "id": "pairwise-scatter",
            "title": f"{x_feature} vs {target_column}",
            "description": "Pairwise scatter chosen from the strongest numeric relationship in the dataset.",
            "chart_type": "scatter",
            "x_key": "x",
            "y_key": "y",
            "series": [{"key": "y", "label": target_column}],
            "data": data,
            "value_format": "number",
        }

    candidates = [column for column in numeric_columns if column != target_column]
    if len(candidates) < 2:
        return None
    corr = df[candidates].corr(numeric_only=True)
    best_pair: Tuple[str, str] | None = None
    best_score = -1.0
    for i, left in enumerate(candidates):
        for right in candidates[i + 1:]:
            value = corr.loc[left, right]
            if pd.notna(value) and abs(float(value)) > best_score:
                best_score = abs(float(value))
                best_pair = (left, right)
    if not best_pair:
        return None
    sample = pd.DataFrame({
        "x": pd.to_numeric(df[best_pair[0]], errors="coerce"),
        "y": pd.to_numeric(df[best_pair[1]], errors="coerce"),
    }).dropna()
    if sample.empty:
        return None
    if len(sample) > 500:
        sample = sample.sample(500, random_state=42)
    data = [{"x": round(float(row.x), 3), "y": round(float(row.y), 3)} for row in sample.itertuples()]
    return {
        "id": "pairwise-scatter",
        "title": f"{best_pair[0]} vs {best_pair[1]}",
        "description": "Pairwise scatter chosen from the most tightly linked numeric feature pair.",
        "chart_type": "scatter",
        "x_key": "x",
        "y_key": "y",
        "series": [{"key": "y", "label": best_pair[1]}],
        "data": data,
        "value_format": "number",
    }


def _build_categorical_target_visual(
    df: pd.DataFrame,
    categorical_columns: List[str],
    target_column: str | None,
) -> Dict[str, Any] | None:
    if not target_column or target_column not in df.columns:
        return None

    if target_column in categorical_columns:
        candidates = [column for column in categorical_columns if column != target_column]
        if not candidates:
            return None
        best_feature = None
        best_score = -1.0
        for column in candidates:
            score = _categorical_association_score(df[column], df[target_column])
            if score > best_score:
                best_feature = column
                best_score = score
        if not best_feature:
            return None
        return _categorical_vs_categorical_chart(df, best_feature, target_column)

    candidates = [column for column in categorical_columns if column != target_column]
    if not candidates:
        return None
    best_feature = max(candidates, key=lambda column: _categorical_priority_score(df[column]))
    return _categorical_vs_numeric_target_chart(df, best_feature, target_column)


def _categorical_vs_categorical_chart(df: pd.DataFrame, feature: str, target_column: str) -> Dict[str, Any] | None:
    feature_values = df[feature].fillna("(Missing)").astype(str)
    target_values = df[target_column].fillna("(Missing)").astype(str)
    top_feature_levels = feature_values.value_counts().head(6).index.tolist()
    top_target_levels = target_values.value_counts().head(4).index.tolist()
    filtered = pd.DataFrame({"feature": feature_values, "target": target_values})
    filtered = filtered[filtered["feature"].isin(top_feature_levels) & filtered["target"].isin(top_target_levels)]
    if filtered.empty:
        return None

    pivot = filtered.groupby(["feature", "target"]).size().unstack(fill_value=0)
    data = []
    for feature_level, row in pivot.iterrows():
        item = {"label": _to_label(feature_level)}
        for target_level in pivot.columns:
            item[_to_label(target_level)] = int(row[target_level])
        data.append(item)

    return {
        "id": "categorical-association",
        "title": f"{feature} by {target_column}",
        "description": "Shows how the most informative categorical feature distributes across target classes.",
        "chart_type": "grouped_bar",
        "x_key": "label",
        "series": [{"key": _to_label(level), "label": _to_label(level)} for level in pivot.columns],
        "data": data,
        "value_format": "count",
    }


def _categorical_vs_numeric_target_chart(df: pd.DataFrame, feature: str, target_column: str) -> Dict[str, Any] | None:
    feature_values = df[feature].fillna("(Missing)").astype(str)
    target_values = pd.to_numeric(df[target_column], errors="coerce")
    merged = pd.DataFrame({"feature": feature_values, "target": target_values}).dropna()
    if merged.empty:
        return None
    top_levels = merged["feature"].value_counts().head(6).index.tolist()
    grouped = merged[merged["feature"].isin(top_levels)].groupby("feature")["target"].agg(["mean", "median"]).reset_index()
    data = [
        {
            "label": _to_label(row["feature"]),
            "mean": round(float(row["mean"]), 3),
            "median": round(float(row["median"]), 3),
        }
        for _, row in grouped.iterrows()
    ]
    return {
        "id": "categorical-target-summary",
        "title": f"{target_column} across {feature}",
        "description": "Compares average and median target values across the most frequent categories.",
        "chart_type": "grouped_bar",
        "x_key": "label",
        "series": [{"key": "mean", "label": "Mean"}, {"key": "median", "label": "Median"}],
        "data": data,
        "value_format": "number",
    }


def _histogram_data(series: pd.Series, bins: int = 12) -> List[Dict[str, Any]]:
    clean = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return []

    unique_count = int(clean.nunique())
    if unique_count <= 12:
        counts = clean.round(3).value_counts().sort_index()
        return [{"bucket": _to_label(index), "count": int(value)} for index, value in counts.items()]

    hist, edges = np.histogram(clean, bins=min(bins, max(unique_count, 1)))
    data = []
    for index, count in enumerate(hist):
        left = edges[index]
        right = edges[index + 1]
        data.append(
            {
                "bucket": f"{left:.2f} to {right:.2f}",
                "count": int(count),
            }
        )
    return data


def _top_counts_data(series: pd.Series) -> List[Dict[str, Any]]:
    counts = series.fillna("(Missing)").astype(str).value_counts()
    if counts.empty:
        return []

    top = counts.head(MAX_TOP_ITEMS)
    data = [{"label": _to_label(index), "count": int(value)} for index, value in top.items()]
    other = int(counts.iloc[MAX_TOP_ITEMS:].sum())
    if other > 0:
        data.append({"label": "Other", "count": other})
    return data


def _numeric_priority_score(series: pd.Series, target: pd.Series | None = None) -> float:
    clean = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    non_null = clean.dropna()
    if non_null.empty:
        return 0.0

    score = float(non_null.std(ddof=0) or 0.0)
    skew = non_null.skew()
    if pd.notna(skew):
        score += abs(float(skew)) * 2
    score += float(clean.isna().mean()) * 5

    if target is not None and is_numeric_dtype(target):
        aligned = pd.concat([clean, pd.to_numeric(target, errors="coerce")], axis=1).dropna()
        if len(aligned) > 2:
            corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
            if pd.notna(corr):
                score += abs(float(corr)) * 10

    return score


def _categorical_priority_score(series: pd.Series) -> float:
    counts = series.fillna("(Missing)").astype(str).value_counts(normalize=True)
    if counts.empty:
        return 0.0
    entropy = float(-(counts * np.log2(counts + 1e-9)).sum())
    coverage_penalty = min(len(counts), 20) / 10
    missing_bonus = float(series.isna().mean()) * 4
    return entropy + coverage_penalty + missing_bonus


def _categorical_association_score(left: pd.Series, right: pd.Series) -> float:
    left_clean = left.fillna("(Missing)").astype(str)
    right_clean = right.fillna("(Missing)").astype(str)
    table = pd.crosstab(left_clean, right_clean)
    if table.empty:
        return 0.0
    joint = table / max(table.values.sum(), 1)
    left_probs = joint.sum(axis=1)
    right_probs = joint.sum(axis=0)
    expected = np.outer(left_probs, right_probs)
    with np.errstate(divide="ignore", invalid="ignore"):
      score = np.nansum(((joint.values - expected) ** 2) / np.where(expected == 0, np.nan, expected))
    return float(score)


def _to_label(value: Any) -> str:
    if pd.isna(value):
        return "(Missing)"
    text = str(value)
    if len(text) > 24:
        return text[:21] + "..."
    return text


def _to_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)
