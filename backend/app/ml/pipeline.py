"""
SigmaCloud AI - AutoML Pipeline
Automatically detects task type, cleans data, trains multiple models,
evaluates performance, and saves results.
"""
import os
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    AdaBoostClassifier,
    AdaBoostRegressor,
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from sklearn.svm import SVC, SVR
from xgboost import XGBClassifier, XGBRegressor

from app.core.config import settings

logger = logging.getLogger(__name__)


class AutoMLPipeline:
    MODEL_ORDER_CLASSIFICATION = [
        "Logistic Regression",
        "Random Forest",
        "Extra Trees",
        "XGBoost",
        "LightGBM",
        "Gradient Boosting",
        "AdaBoost",
        "SVC",
        "KNN",
    ]
    MODEL_ORDER_REGRESSION = [
        "Ridge Regression",
        "Elastic Net",
        "Random Forest",
        "Extra Trees",
        "XGBoost",
        "LightGBM",
        "Gradient Boosting",
        "AdaBoost",
        "SVR",
        "KNN",
    ]

    def __init__(self, job_id: str, progress_callback=None):
        self.job_id = job_id
        self.progress_callback = progress_callback
        self.label_encoder = None
        self.feature_names: List[str] = []

    def _update_progress(self, progress: int, message: str = ""):
        if self.progress_callback:
            self.progress_callback(progress, message)
        logger.info("[%s] Progress %s%%: %s", self.job_id, progress, message)

    def detect_task_type(self, y: pd.Series) -> str:
        n_unique = y.nunique()
        dtype = y.dtype

        if dtype == "object" or dtype == "bool" or str(dtype) == "category":
            return "classification"

        # A small integer-valued target with few distinct values is almost
        # always a class label. The ratio test alone mislabels small datasets:
        # a 30-row binary target scores 2/30 = 0.067 and used to fall through
        # to regression.
        is_integral = pd.api.types.is_integer_dtype(y) or (
            pd.api.types.is_float_dtype(y) and float(y.dropna().mod(1).abs().max() or 0) == 0.0
        )
        if is_integral and n_unique <= 20:
            return "classification"

        if n_unique <= 20 and n_unique / max(len(y), 1) < 0.05:
            return "classification"

        return "regression"

    def build_training_plan(
        self,
        df: pd.DataFrame,
        target_column: str,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        preview_df = df.copy()
        if target_column not in preview_df.columns:
            raise ValueError(f"Target column '{target_column}' not found")

        inferred_task_type = task_type if task_type and task_type != "auto" else self.detect_task_type(preview_df[target_column].dropna())
        numeric_columns, categorical_columns = self._classify_features(preview_df.drop(columns=[target_column]), target_column)
        cleaning_preview = self._build_cleaning_preview(preview_df, target_column, numeric_columns, categorical_columns)
        recommended_models, recommendation_reasons = self._recommend_models(
            row_count=len(preview_df),
            numeric_count=len(numeric_columns),
            categorical_count=len(categorical_columns),
            task_type=inferred_task_type,
        )

        return {
            "task_type": inferred_task_type,
            "available_models": self.available_models(inferred_task_type),
            "recommended_models": recommended_models,
            "recommendation_reasons": recommendation_reasons,
            "cleaning_preview": cleaning_preview,
        }

    def available_models(self, task_type: str) -> List[str]:
        return self.MODEL_ORDER_CLASSIFICATION if task_type == "classification" else self.MODEL_ORDER_REGRESSION

    def preprocess(
        self,
        df: pd.DataFrame,
        target_column: str,
        task_type: str,
        test_size: float = 0.2,
    ) -> Tuple[Any, Any, Any, Any, ColumnTransformer, List[str], List[str]]:
        df = df.copy()
        cleaning_steps: List[str] = []

        duplicate_count = int(df.duplicated().sum())
        if duplicate_count:
            df = df.drop_duplicates()
            cleaning_steps.append(f"Removed {duplicate_count} duplicate rows before modeling.")

        target_missing = int(df[target_column].isna().sum())
        if target_missing:
            df = df.dropna(subset=[target_column])
            cleaning_steps.append(f"Dropped {target_missing} rows with missing target values.")

        X = df.drop(columns=[target_column])
        y = df[target_column].copy()

        num_cols, cat_cols = self._classify_features(X, target_column)
        high_cardinality = [column for column in cat_cols if X[column].nunique(dropna=True) > 50]
        if high_cardinality:
            X = X.drop(columns=high_cardinality)
            cat_cols = [column for column in cat_cols if column not in high_cardinality]
            cleaning_steps.append(
                "Dropped high-cardinality categorical columns: " + ", ".join(high_cardinality[:6])
            )

        missing_num_cols = [column for column in num_cols if X[column].isna().any()]
        missing_cat_cols = [column for column in cat_cols if X[column].isna().any()]
        if missing_num_cols:
            cleaning_steps.append("Median-imputed numeric columns with missing values.")
        if missing_cat_cols:
            cleaning_steps.append("Mode-imputed categorical columns with missing values.")

        if num_cols:
            cleaning_steps.append("Standardized numeric features for stable optimization.")
        if cat_cols:
            cleaning_steps.append("One-hot encoded categorical features and kept unseen categories safe.")

        self.feature_names = num_cols + cat_cols
        X = X[self.feature_names]

        num_transformer = Pipeline(
            [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
        )
        cat_transformer = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", num_transformer, num_cols),
                ("cat", cat_transformer, cat_cols),
            ],
            remainder="drop",
        )

        if task_type == "classification":
            if not pd.api.types.is_numeric_dtype(y) or pd.api.types.is_bool_dtype(y):
                self.label_encoder = LabelEncoder()
                y = pd.Series(
                    self.label_encoder.fit_transform(y.astype(str)),
                    name=target_column,
                    index=y.index,
                )
                cleaning_steps.append("Encoded target labels into numeric classes.")

        stratify_target = y if task_type == "classification" and y.nunique() < 20 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=settings.RANDOM_STATE,
            stratify=stratify_target,
        )

        return X_train, X_test, y_train, y_test, preprocessor, self.feature_names, cleaning_steps

    def get_feature_importances(
        self,
        model: Pipeline,
        preprocessor: ColumnTransformer,
        feature_names: List[str],
    ) -> Dict[str, float]:
        try:
            estimator = model.named_steps.get("classifier") or model.named_steps.get("regressor")
            if estimator is None:
                return {}

            if hasattr(estimator, "feature_importances_"):
                importances = np.asarray(estimator.feature_importances_, dtype=float)
            elif hasattr(estimator, "coef_"):
                importances = np.abs(np.asarray(estimator.coef_, dtype=float)).ravel()
            else:
                return {}

            # Width per original column, taken from each transformer's own
            # fitted state. Deriving it by name-prefix matching silently
            # misaligned every subsequent column whenever one feature name was
            # a prefix of another (e.g. "age" and "age_group").
            column_widths: List[Tuple[str, int]] = []
            for name, transformer, cols in preprocessor.transformers_:
                if name == "num":
                    column_widths.extend((column, 1) for column in cols)
                elif name == "cat":
                    encoder = transformer.named_steps.get("encoder")
                    categories = getattr(encoder, "categories_", None)
                    if categories is None:
                        column_widths.extend((column, 1) for column in cols)
                    else:
                        column_widths.extend(
                            (column, len(values)) for column, values in zip(cols, categories)
                        )

            expected_width = sum(width for _, width in column_widths)
            if expected_width != importances.shape[0]:
                logger.warning(
                    "Feature importance width mismatch (expected %s, got %s) - skipping",
                    expected_width,
                    importances.shape[0],
                )
                return {}

            grouped: Dict[str, float] = {}
            offset = 0
            for column, width in column_widths:
                grouped[column] = float(np.sum(importances[offset:offset + width]))
                offset += width

            total = sum(grouped.values())
            if total > 0:
                grouped = {name: value / total for name, value in grouped.items()}

            return dict(sorted(grouped.items(), key=lambda item: item[1], reverse=True)[:20])
        except Exception as exc:
            logger.warning("Could not extract feature importances: %s", exc)
            return {}

    def evaluate_classification(
        self,
        pipeline: Pipeline,
        X_test,
        y_test,
        X_train,
        y_train,
        cv_folds: int,
    ) -> Dict[str, Any]:
        y_pred = pipeline.predict(X_test)
        metrics: Dict[str, Any] = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "f1_score": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        }

        try:
            n_classes = len(np.unique(y_test))
            if n_classes == 2 and hasattr(pipeline, "predict_proba"):
                y_prob = pipeline.predict_proba(X_test)[:, 1]
                metrics["roc_auc"] = float(roc_auc_score(y_test, y_prob))
                fpr, tpr, _ = roc_curve(y_test, y_prob)
                metrics["roc_curve"] = {"fpr": fpr.tolist(), "tpr": tpr.tolist()}
            elif hasattr(pipeline, "predict_proba"):
                y_prob = pipeline.predict_proba(X_test)
                metrics["roc_auc"] = float(
                    roc_auc_score(y_test, y_prob, multi_class="ovr", average="weighted")
                )
        except Exception:
            metrics["roc_auc"] = None

        metrics["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()

        # Cross-validate on the training split only. Folding over train+test
        # let the held-out rows influence the CV score, so the two numbers were
        # not independent - and it refit on 25% more data every fold.
        effective_folds = self._safe_fold_count(y_train, cv_folds, stratified=True)
        if effective_folds:
            cv = StratifiedKFold(
                n_splits=effective_folds, shuffle=True, random_state=settings.RANDOM_STATE
            )
            cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")
            metrics["cv_scores"] = cv_scores.tolist()
            metrics["cv_mean"] = float(cv_scores.mean())
            metrics["cv_std"] = float(cv_scores.std())
            metrics["cv_folds"] = effective_folds

        return metrics

    def evaluate_regression(
        self,
        pipeline: Pipeline,
        X_test,
        y_test,
        X_train,
        y_train,
        cv_folds: int,
    ) -> Dict[str, Any]:
        y_pred = pipeline.predict(X_test)
        metrics: Dict[str, Any] = {
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "r2_score": float(r2_score(y_test, y_pred)),
            "residuals": {
                "predicted": y_pred.tolist()[:200],
                "actual": y_test.tolist()[:200],
            },
        }

        # See evaluate_classification: CV runs on the training split only.
        effective_folds = self._safe_fold_count(y_train, cv_folds, stratified=False)
        if effective_folds:
            cv = KFold(n_splits=effective_folds, shuffle=True, random_state=settings.RANDOM_STATE)
            cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="r2")
            metrics["cv_scores"] = cv_scores.tolist()
            metrics["cv_mean"] = float(cv_scores.mean())
            metrics["cv_std"] = float(cv_scores.std())
            metrics["cv_folds"] = effective_folds

        return metrics

    @staticmethod
    def _safe_fold_count(y_train, requested_folds: int, stratified: bool) -> int:
        """Clamp folds to what the training split can actually support.

        StratifiedKFold raises when a class has fewer members than folds, which
        previously failed the whole model instead of degrading the CV estimate.
        Returns 0 when cross-validation is not possible at all.
        """
        n_samples = len(y_train)
        if n_samples < 4:
            return 0

        folds = min(requested_folds, n_samples)
        if stratified:
            smallest_class = int(pd.Series(y_train).value_counts().min())
            folds = min(folds, smallest_class)

        return folds if folds >= 2 else 0

    def train_all_models(
        self,
        df: pd.DataFrame,
        target_column: str,
        task_type: Optional[str] = None,
        test_size: float = 0.2,
        cv_folds: int = 5,
        models_to_train: Optional[List[str]] = None,
        mode: str = "simple",
        tuning_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self._update_progress(5, "Analyzing dataset and planning training...")

        plan = self.build_training_plan(df, target_column, task_type)
        task_type = plan["task_type"]
        selected_models = models_to_train or (plan["recommended_models"] if mode == "simple" else plan["available_models"])

        self._update_progress(10, "Cleaning and preprocessing data...")
        X_train, X_test, y_train, y_test, preprocessor, feature_names, cleaning_steps = self.preprocess(
            df,
            target_column,
            task_type,
            test_size,
        )

        model_catalog = self._build_models(task_type, mode, tuning_params or {})
        model_catalog = {name: estimator for name, estimator in model_catalog.items() if name in selected_models}
        results: List[Dict[str, Any]] = []
        n_models = max(len(model_catalog), 1)

        for index, (model_name, estimator) in enumerate(model_catalog.items()):
            progress = 12 + int((index / n_models) * 82)
            self._update_progress(progress, f"Training {model_name}...")

            try:
                start = time.time()
                step_name = "classifier" if task_type == "classification" else "regressor"
                # Clone the preprocessor per model: sharing one fitted instance
                # across every pipeline in the loop means each fit mutates the
                # state the previously-saved models still reference.
                pipeline = Pipeline(
                    [("preprocessor", clone(preprocessor)), (step_name, estimator)]
                )
                pipeline.fit(X_train, y_train)
                training_time = time.time() - start

                metrics = (
                    self.evaluate_classification(pipeline, X_test, y_test, X_train, y_train, cv_folds)
                    if task_type == "classification"
                    else self.evaluate_regression(pipeline, X_test, y_test, X_train, y_train, cv_folds)
                )

                feature_importance = self.get_feature_importances(
                    pipeline, pipeline.named_steps["preprocessor"], feature_names
                )
                model_filename = f"{self.job_id}_{model_name.replace(' ', '_')}.joblib"
                model_path = os.path.join(settings.MODEL_STORAGE_PATH, model_filename)
                joblib.dump(
                    {
                        "pipeline": pipeline,
                        "feature_names": feature_names,
                        "label_encoder": self.label_encoder,
                        "task_type": task_type,
                        "model_name": model_name,
                        "cleaning_steps": cleaning_steps,
                    },
                    model_path,
                )

                results.append(
                    {
                        "model_name": model_name,
                        "model_type": type(estimator).__name__,
                        "task_type": task_type,
                        "file_path": model_path,
                        "metrics": metrics,
                        "feature_importance": feature_importance,
                        "training_time": training_time,
                        "accuracy": metrics.get("accuracy"),
                        "f1_score": metrics.get("f1_score"),
                        "roc_auc": metrics.get("roc_auc"),
                        "rmse": metrics.get("rmse"),
                        "mae": metrics.get("mae"),
                        "r2_score": metrics.get("r2_score"),
                        "confusion_matrix": metrics.get("confusion_matrix"),
                        "roc_curve_data": metrics.get("roc_curve"),
                        "cv_scores": metrics.get("cv_scores"),
                        "cv_mean": metrics.get("cv_mean"),
                        "cv_std": metrics.get("cv_std"),
                    }
                )
                logger.info("Model %s trained in %.2fs", model_name, training_time)
            except Exception as exc:
                logger.exception("Failed to train %s: %s", model_name, exc)
                results.append(
                    {
                        "model_name": model_name,
                        "model_type": type(estimator).__name__,
                        "task_type": task_type,
                        "error": str(exc),
                        "training_time": 0,
                    }
                )

        self._update_progress(100, "Training complete!")
        return {
            "task_type": task_type,
            "models": results,
            "feature_names": feature_names,
            "cleaning_steps": cleaning_steps,
            "recommended_models": plan["recommended_models"],
            "recommendation_reasons": plan["recommendation_reasons"],
            "available_models": plan["available_models"],
            "selected_models": selected_models,
            "mode": mode,
        }

    def _classify_features(self, X: pd.DataFrame, target_column: str | None = None) -> Tuple[List[str], List[str]]:
        """Split columns into numeric and categorical.

        Uses dtype predicates rather than an explicit int64/float64 list:
        database imports routinely produce int32, float32, nullable Int64 and
        Decimal columns, all of which were previously dropped from both groups
        and silently excluded from training.
        """
        num_cols: List[str] = []
        cat_cols: List[str] = []

        for column in X.columns:
            series = X[column]

            if pd.api.types.is_bool_dtype(series):
                cat_cols.append(column)
            elif pd.api.types.is_numeric_dtype(series):
                num_cols.append(column)
            elif pd.api.types.is_datetime64_any_dtype(series):
                # Raw timestamps are not usable by these estimators and would
                # blow up one-hot encoding; skipped rather than mis-encoded.
                continue
            else:
                cat_cols.append(column)

        return num_cols, cat_cols

    def _build_cleaning_preview(
        self,
        df: pd.DataFrame,
        target_column: str,
        num_cols: List[str],
        cat_cols: List[str],
    ) -> List[str]:
        preview: List[str] = []
        duplicate_count = int(df.duplicated().sum())
        if duplicate_count:
            preview.append(f"Duplicate rows would be removed ({duplicate_count}).")
        target_missing = int(df[target_column].isna().sum())
        if target_missing:
            preview.append(f"Rows with missing target values would be dropped ({target_missing}).")
        if any(df[column].isna().any() for column in num_cols):
            preview.append("Numeric columns with gaps will be median-imputed.")
        if any(df[column].isna().any() for column in cat_cols):
            preview.append("Categorical columns with gaps will be mode-imputed.")
        high_cardinality = [column for column in cat_cols if df[column].nunique(dropna=True) > 50]
        if high_cardinality:
            preview.append("High-cardinality categorical columns will be excluded to keep encoding stable.")
        if num_cols:
            preview.append("Numeric features will be standardized.")
        if cat_cols:
            preview.append("Categorical features will be one-hot encoded.")
        return preview

    def _recommend_models(
        self,
        row_count: int,
        numeric_count: int,
        categorical_count: int,
        task_type: str,
    ) -> Tuple[List[str], List[str]]:
        recommendations: List[str] = []
        reasons: List[str] = []

        if task_type == "classification":
            recommendations.append("Logistic Regression")
            reasons.append("Logistic Regression gives a strong baseline and interpretable coefficients.")
            recommendations.append("Random Forest")
            reasons.append("Random Forest handles mixed features and non-linear splits well.")
            if row_count > 3000 or categorical_count > 0:
                recommendations.append("LightGBM")
                reasons.append("LightGBM is recommended for larger or mixed-type datasets with strong boosting performance.")
            if numeric_count <= 20 and row_count < 5000:
                recommendations.append("SVC")
                reasons.append("SVC is useful on smaller feature spaces where tighter decision boundaries matter.")
            else:
                recommendations.append("XGBoost")
                reasons.append("XGBoost is recommended for robust boosted performance on richer datasets.")
        else:
            recommendations.append("Ridge Regression")
            reasons.append("Ridge Regression gives a stable baseline for numeric prediction.")
            recommendations.append("Random Forest")
            reasons.append("Random Forest captures non-linear regression patterns without much tuning.")
            if row_count > 3000 or categorical_count > 0:
                recommendations.append("LightGBM")
                reasons.append("LightGBM is recommended for efficient boosting on larger regression datasets.")
            if numeric_count <= 20 and row_count < 4000:
                recommendations.append("SVR")
                reasons.append("SVR is a good option for smaller numeric regression datasets.")
            else:
                recommendations.append("XGBoost")
                reasons.append("XGBoost is recommended for strong non-linear regression performance.")

        unique_recommendations = []
        for model in recommendations:
            if model not in unique_recommendations:
                unique_recommendations.append(model)
        return unique_recommendations[:4], reasons[:4]

    def _apply_tuning(self, estimator, tuning_values: Dict[str, Any]):
        if not tuning_values:
            return estimator
        valid_params = estimator.get_params()
        filtered = {
            key: value
            for key, value in tuning_values.items()
            if key in valid_params and value not in (None, "", "auto")
        }
        if filtered:
            estimator.set_params(**filtered)
        return estimator

    def _build_models(
        self,
        task_type: str,
        mode: str,
        tuning_params: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        estimator_boost = 200 if mode == "complex" else 120
        tree_depth = None if mode == "complex" else 10

        if task_type == "classification":
            models = {
                "Logistic Regression": LogisticRegression(max_iter=1500, C=1.0, random_state=settings.RANDOM_STATE),
                "Random Forest": RandomForestClassifier(n_estimators=estimator_boost, max_depth=tree_depth, random_state=settings.RANDOM_STATE),
                "Extra Trees": ExtraTreesClassifier(n_estimators=estimator_boost, max_depth=tree_depth, random_state=settings.RANDOM_STATE),
                "XGBoost": XGBClassifier(n_estimators=estimator_boost, max_depth=6 if mode == "complex" else 4, learning_rate=0.08, random_state=settings.RANDOM_STATE, eval_metric="logloss", verbosity=0),
                "LightGBM": LGBMClassifier(n_estimators=estimator_boost, learning_rate=0.08, max_depth=-1 if mode == "complex" else 8, random_state=settings.RANDOM_STATE, verbose=-1),
                "Gradient Boosting": GradientBoostingClassifier(n_estimators=estimator_boost, learning_rate=0.08),
                "AdaBoost": AdaBoostClassifier(n_estimators=estimator_boost // 2, learning_rate=0.8, random_state=settings.RANDOM_STATE),
                "SVC": SVC(C=1.0, probability=True, random_state=settings.RANDOM_STATE),
                "KNN": KNeighborsClassifier(n_neighbors=7),
            }
            order = self.MODEL_ORDER_CLASSIFICATION
        else:
            models = {
                "Ridge Regression": Ridge(alpha=1.0, random_state=settings.RANDOM_STATE),
                "Elastic Net": ElasticNet(alpha=0.05, l1_ratio=0.5, random_state=settings.RANDOM_STATE),
                "Random Forest": RandomForestRegressor(n_estimators=estimator_boost, max_depth=tree_depth, random_state=settings.RANDOM_STATE),
                "Extra Trees": ExtraTreesRegressor(n_estimators=estimator_boost, max_depth=tree_depth, random_state=settings.RANDOM_STATE),
                "XGBoost": XGBRegressor(n_estimators=estimator_boost, max_depth=6 if mode == "complex" else 4, learning_rate=0.08, random_state=settings.RANDOM_STATE, verbosity=0),
                "LightGBM": LGBMRegressor(n_estimators=estimator_boost, learning_rate=0.08, max_depth=-1 if mode == "complex" else 8, random_state=settings.RANDOM_STATE, verbose=-1),
                "Gradient Boosting": GradientBoostingRegressor(n_estimators=estimator_boost, learning_rate=0.08, random_state=settings.RANDOM_STATE),
                "AdaBoost": AdaBoostRegressor(n_estimators=estimator_boost // 2, learning_rate=0.8, random_state=settings.RANDOM_STATE),
                "SVR": SVR(C=1.0, epsilon=0.1),
                "KNN": KNeighborsRegressor(n_neighbors=7),
            }
            order = self.MODEL_ORDER_REGRESSION

        tuned = {name: self._apply_tuning(estimator, tuning_params.get(name, {})) for name, estimator in models.items()}
        return {name: tuned[name] for name in order if name in tuned}
