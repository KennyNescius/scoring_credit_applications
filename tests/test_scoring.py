"""
test_scoring.py — автоматические тесты для скорингового движка.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from data_loader import build_feature_dataset, FEATURE_COLUMNS, aggregate_monthly_flows, aggregate_existing_loans
from scoring_engine import CreditScoringEngine, SCORE_THRESHOLD


@pytest.fixture(scope="module")
def dataset():
    """Загрузка датасета (один раз на модуль)."""
    return build_feature_dataset()


@pytest.fixture(scope="module")
def engine(dataset):
    """Обученный движок."""
    eng = CreditScoringEngine()
    eng.train(dataset)
    return eng


class TestDataLoading:
    """Тесты загрузки данных."""

    def test_dataset_shape(self, dataset):
        assert len(dataset) == 2700, "Должно быть 2700 заявок"

    def test_train_test_split(self, dataset):
        train = dataset[dataset["target"].notna()]
        test = dataset[dataset["target"].isna()]
        assert len(train) == 2160, "Train: 2160 заявок"
        assert len(test) == 540, "Test: 540 заявок"

    def test_features_no_nulls(self, dataset):
        for col in FEATURE_COLUMNS:
            assert dataset[col].isna().sum() == 0, f"Нет пропусков в {col}"

    def test_dti_range(self, dataset):
        assert dataset["dti"].min() >= 0, "DTI >= 0"
        assert dataset["dti"].max() <= 5, "DTI <= 5 (clipped)"

    def test_pti_range(self, dataset):
        assert dataset["pti"].min() >= 0, "PTI >= 0"
        assert dataset["pti"].max() <= 5, "PTI <= 5 (clipped)"

    def test_income_cv_non_negative(self, dataset):
        assert (dataset["income_cv"] >= 0).all(), "CV дохода >= 0"


class TestScoringEngine:
    """Тесты скорингового движка."""

    def test_model_trained(self, engine):
        assert engine.is_trained, "Модель должна быть обучена"

    def test_predict_pd_shape(self, engine, dataset):
        X = dataset[FEATURE_COLUMNS].values[:10]
        pd_vals = engine.predict_pd(X)
        assert len(pd_vals) == 10
        assert all(0 <= p <= 1 for p in pd_vals), "PD в диапазоне [0, 1]"

    def test_score_range(self, engine, dataset):
        X = dataset[FEATURE_COLUMNS].values
        pd_vals = engine.predict_pd(X)
        scores = engine.pd_to_score(pd_vals)
        assert all(0 <= s <= 1000 for s in scores), "Скор в диапазоне [0, 1000]"

    def test_score_application_returns_factors(self, engine, dataset):
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        result = engine.score_application(features)

        assert "score" in result
        assert "pd" in result
        assert "decision" in result
        assert "factors" in result
        assert "reason" in result
        assert len(result["factors"]) > 0, "Должны быть факторы"

    def test_decision_logic(self, engine, dataset):
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        result = engine.score_application(features)

        if result["score"] >= SCORE_THRESHOLD:
            assert result["decision"] == "toladi"
        else:
            assert result["decision"] == "defolt"

    def test_factor_explanation_has_points(self, engine, dataset):
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        result = engine.score_application(features)

        for factor in result["factors"]:
            assert "feature_name" in factor
            assert "points" in factor
            assert "direction" in factor
            assert factor["direction"] in ("positive", "negative")

    def test_reason_text_not_empty(self, engine, dataset):
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        result = engine.score_application(features)
        assert len(result["reason"]) > 10, "Причина не должна быть пустой"

    def test_high_dti_increases_risk(self, engine, dataset):
        """Высокий DTI должен увеличивать риск (выше PD, ниже скор)."""
        row = dataset.iloc[0]
        features_low = {f: row[f] for f in FEATURE_COLUMNS}
        features_low["dti"] = 0.1
        features_low["pti"] = 0.2

        features_high = features_low.copy()
        features_high["dti"] = 0.9
        features_high["pti"] = 1.5

        result_low = engine.score_application(features_low)
        result_high = engine.score_application(features_high)

        assert result_high["pd"] > result_low["pd"], "Высокий DTI → выше PD"

    def test_find_max_limit(self, engine, dataset):
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        features["deklaratsiya_daromad"] = row.get("deklaratsiya_daromad", 3000000)
        limit = engine.find_max_limit(features)
        assert limit >= 0, "Лимит >= 0"


class TestResultsFile:
    """Тесты генерации файла результатов."""

    def test_generate_results(self, engine, dataset):
        result_df = engine.generate_results_file(dataset)
        assert len(result_df) == 540, "Должно быть 540 тестовых заявок"
        assert "application_id" in result_df.columns
        assert "score" in result_df.columns
        assert "sabab" in result_df.columns

    def test_all_test_applications_present(self, engine, dataset):
        result_df = engine.generate_results_file(dataset)
        test_ids = dataset[dataset["target"].isna()]["application_id"].tolist()
        result_ids = result_df["application_id"].tolist()
        assert set(test_ids) == set(result_ids), "Все test заявки должны быть в результате"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
