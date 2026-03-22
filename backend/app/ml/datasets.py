"""
SigmaCloud AI - Example Dataset Loaders
Provides California Housing, Titanic, and Breast Cancer datasets.
"""
import pandas as pd
import numpy as np
from sklearn.datasets import (
    fetch_california_housing,
    load_breast_cancer,
    load_iris,
    load_wine,
)
from typing import Tuple


def load_titanic() -> pd.DataFrame:
    """Load a synthetic Titanic-like dataset."""
    np.random.seed(42)
    n = 891

    df = pd.DataFrame({
        "pclass": np.random.choice([1, 2, 3], n, p=[0.24, 0.21, 0.55]),
        "sex": np.random.choice(["male", "female"], n, p=[0.65, 0.35]),
        "age": np.random.normal(29.7, 14.5, n).clip(1, 80),
        "sibsp": np.random.choice([0, 1, 2, 3, 4, 5, 8], n, p=[0.68, 0.23, 0.03, 0.02, 0.02, 0.01, 0.01]),
        "parch": np.random.choice([0, 1, 2, 3, 4, 5, 6], n, p=[0.76, 0.13, 0.09, 0.005, 0.004, 0.004, 0.003]),
        "fare": np.random.lognormal(3.2, 1.2, n).clip(3.2, 512),
        "embarked": np.random.choice(["S", "C", "Q"], n, p=[0.72, 0.19, 0.09]),
    })

    # Introduce missing values
    df.loc[np.random.choice(n, 177, replace=False), "age"] = np.nan
    df.loc[np.random.choice(n, 2, replace=False), "embarked"] = np.nan

    # Target based on realistic survival rules
    survival_prob = (
        0.1
        + 0.3 * (df["sex"] == "female")
        + 0.25 * (df["pclass"] == 1)
        + 0.1 * (df["pclass"] == 2)
        - 0.1 * (df["age"].fillna(30) > 60)
    ).clip(0, 1)
    df["survived"] = (np.random.rand(n) < survival_prob).astype(int)

    return df


def load_california_housing_df() -> pd.DataFrame:
    """Load California Housing dataset as DataFrame."""
    data = fetch_california_housing()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["MedHouseVal"] = data.target
    return df


def load_breast_cancer_df() -> pd.DataFrame:
    """Load Breast Cancer dataset as DataFrame."""
    data = load_breast_cancer()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["diagnosis"] = data.target
    df["diagnosis"] = df["diagnosis"].map({0: "malignant", 1: "benign"})
    return df


def load_iris_df() -> pd.DataFrame:
    """Load Iris dataset as DataFrame."""
    data = load_iris()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["species"] = [data.target_names[i] for i in data.target]
    return df


EXAMPLE_DATASETS = {
    "california_housing": {
        "name": "California Housing",
        "description": "Predict median house values in California districts",
        "loader": load_california_housing_df,
        "target": "MedHouseVal",
        "task_type": "regression",
        "filename": "california_housing.csv",
    },
    "titanic": {
        "name": "Titanic Survival",
        "description": "Predict passenger survival on the Titanic",
        "loader": load_titanic,
        "target": "survived",
        "task_type": "classification",
        "filename": "titanic.csv",
    },
    "breast_cancer": {
        "name": "Breast Cancer",
        "description": "Classify breast cancer tumors as malignant or benign",
        "loader": load_breast_cancer_df,
        "target": "diagnosis",
        "task_type": "classification",
        "filename": "breast_cancer.csv",
    },
    "iris": {
        "name": "Iris Flowers",
        "description": "Classify Iris flowers into 3 species",
        "loader": load_iris_df,
        "target": "species",
        "task_type": "classification",
        "filename": "iris.csv",
    },
}
