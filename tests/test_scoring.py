"""
test_scoring.py — автоматические тесты для скорингового движка.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import pytest
import numpy as np
import db as db_module
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

    def test_reason_text_not_empty_for_rejection(self, engine, dataset):
        # generate_reason_text() only fills `reason` for decision == "defolt"
        # (an approval has nothing to explain away) -- row 0 happens to be an
        # approval, so force a clearly bad profile to actually exercise the
        # rejection path this test is named for.
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        features["dti"] = 0.9
        features["pti"] = 1.5
        result = engine.score_application(features)
        assert result["decision"] == "defolt", "Bu profil rad etilishi kerak edi"
        assert len(result["reason"]) > 10, "Причина не должна быть пустой"

    def test_reason_text_empty_for_approval(self, engine, dataset):
        row = dataset.iloc[0]
        features = {f: row[f] for f in FEATURE_COLUMNS}
        features["dti"] = 0.05
        features["pti"] = 0.05
        result = engine.score_application(features)
        assert result["decision"] == "toladi", "Bu profil tasdiqlanishi kerak edi"
        assert result["reason"] == "", "Tasdiqlash uchun sabab bo'lmasligi kerak"

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


class TestPersistence:
    """Immutable decision log + SCD Type 2 (db.py) -- Base requirement из ТЗ.
    Изолировано от боевого credit_scoring.db через monkeypatch DB_PATH."""

    @pytest.fixture
    def isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
        db_module.init_db()
        return db_module

    def test_no_update_or_delete_api_exists(self):
        # "Immutable" is only true if there's no code path that can mutate a
        # decision after the fact -- assert the API surface itself forbids it.
        assert not hasattr(db_module, "update_decision")
        assert not hasattr(db_module, "delete_decision")

    def test_publish_scorecard_version_is_scd2(self, isolated_db):
        v1 = isolated_db.publish_scorecard_version(model_path="m1.pkl", train_auc=0.80)
        v2 = isolated_db.publish_scorecard_version(model_path="m2.pkl", train_auc=0.81)

        row1 = isolated_db.get_scorecard_version(v1)
        row2 = isolated_db.get_scorecard_version(v2)
        assert row1["valid_to"] is not None, "старая версия должна быть закрыта, а не удалена"
        assert row2["valid_to"] is None, "новая версия должна быть активной"
        assert isolated_db.get_active_scorecard_version()["version_id"] == v2

    def test_insert_and_read_decision_round_trip(self, isolated_db):
        v1 = isolated_db.publish_scorecard_version(model_path="m.pkl")
        isolated_db.insert_decision(
            application_id="AP_TEST", applicant_id="A_TEST", scorecard_version_id=v1,
            score=500, pd_value=0.1, decision="toladi", threshold=450,
            factors=[{"feature": "dti", "points": 10, "direction": "positive"}],
            input_snapshot={"dti": 0.2}, source="dataset",
        )
        row = isolated_db.get_latest_decision_for_application("AP_TEST")
        assert row is not None
        assert row["score"] == 500
        assert row["decision"] == "toladi"
        # factors are stored language-agnostic (feature key + points), not
        # pre-rendered text -- app.py regenerates labels at display time.
        assert json.loads(row["factors_json"])[0]["feature"] == "dti"

    def test_old_decision_keeps_pointing_at_its_own_scorecard_version(self, isolated_db):
        v1 = isolated_db.publish_scorecard_version(model_path="m1.pkl")
        isolated_db.insert_decision(
            application_id="AP1", applicant_id="A1", scorecard_version_id=v1,
            score=400, pd_value=0.3, decision="defolt", threshold=450,
            factors=[], input_snapshot={}, source="dataset",
        )
        isolated_db.publish_scorecard_version(model_path="m2.pkl")  # retrain -> v2 active

        row = isolated_db.get_latest_decision_for_application("AP1")
        assert row["scorecard_version_id"] == v1, "старое решение не должно 'переехать' на новую версию"

    def test_list_latest_decisions_dedupes_per_application(self, isolated_db):
        v1 = isolated_db.publish_scorecard_version(model_path="m1.pkl")
        for score in (400, 420, 440):  # simulate 3 re-scores of the same application
            isolated_db.insert_decision(
                application_id="AP1", applicant_id="A1", scorecard_version_id=v1,
                score=score, pd_value=0.3, decision="defolt", threshold=450,
                factors=[], input_snapshot={}, source="dataset",
            )
        latest = isolated_db.list_latest_decisions()
        matching = [r for r in latest if r["application_id"] == "AP1"]
        assert len(matching) == 1, "должна остаться ровно одна (последняя) запись на заявку"
        assert matching[0]["score"] == 440


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
