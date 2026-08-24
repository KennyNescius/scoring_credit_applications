"""
scoring_engine.py — Скоринговый движок: обучение модели, предсказание, объяснение решений.

Алгоритмы:
  1. DTI/PTI — Debt-to-Income / Payment-to-Income (обязательный)
  2. Cash-flow анализ — CV дохода, медиана (обязательный)
  3. WOE/IV биннинг (бонус)
  4. Логистическая регрессия (бонус)
  5. Binary search для лимита (бонус)
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from data_loader import (
    build_feature_dataset,
    load_test_answers,
    FEATURE_COLUMNS,
)
from translations import translate

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")
RESULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "natija")

# Scorecard параметры
BASE_SCORE = 500
PDO = 50  # Points to Double Odds
BASE_ODDS = 19  # odds at base score (19:1 = ~5% default rate)
FACTOR = PDO / np.log(2)
OFFSET = BASE_SCORE - FACTOR * np.log(BASE_ODDS)

# Порог решения
SCORE_THRESHOLD = 450  # ниже — отказ

# Affordability-потолок для find_max_limit(): скор-модель одна не гарантирует
# реалистичность лимита -- достаточно "хороших" по остальным фичам заявителей
# модель одобряла даже там, где новый платёж физически превышал бы весь
# месячный доход (PTI > 100%), поскольку другие положительные факторы
# перевешивали штраф за высокий PTI в сумме баллов. Это отдельное жёсткое
# бизнес-правило поверх скора, а не то, чему учили логрегрессию.
MAX_PTI_FOR_LIMIT_SEARCH = 0.5  # платёж по новому + существующим кредитам не выше 50% дохода


class CreditScoringEngine:
    """Основной скоринговый движок."""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_columns = FEATURE_COLUMNS
        self.feature_means = None  # baseline для объяснений
        self.is_trained = False
        self.version = "v1.0"
        self.version_date = None
        self.version_id = None  # scorecard_versions.version_id (SCD Type 2, db.py)
        self.woe_bins = {}  # WOE биннинг
        self.target_encodings = {}
        self.clip_thresholds = {}

    def train(self, df=None):
        """Обучение модели на train-данных."""
        if df is None:
            df = build_feature_dataset()

        train_df = df[df["target"].notna()].copy()
        y_train = train_df["target"].values
        
        # Target Encoding
        target_cols = ["bandlik_encoded", "talim_encoded", "maqsad_encoded"]
        for col in target_cols:
            means = train_df.groupby(col)["target"].mean().to_dict()
            global_mean = y_train.mean()
            self.target_encodings[col] = {"means": means, "global_mean": global_mean}
            train_df[col] = train_df[col].map(means).fillna(global_mean)
            
        # Winsorization (Clipping)
        for col in self.feature_columns:
            if col not in target_cols:
                lower = train_df[col].quantile(0.01)
                upper = train_df[col].quantile(0.99)
                self.clip_thresholds[col] = (lower, upper)
                train_df[col] = train_df[col].clip(lower, upper)
                
        X_train = train_df[self.feature_columns].values

        # Масштабирование
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_train)

        # Сохраняем средние значения для baseline объяснений
        self.feature_means = dict(zip(
            self.feature_columns,
            train_df[self.feature_columns].mean().values
        ))

        # WOE/IV биннинг для ключевых фичей (аналитика)
        self._compute_woe(train_df, y_train)

        # Логистическая регрессия с тюнингом гиперпараметров
        # Используем class_weight=None чтобы PD соответствовал реальным вероятностям (а не 50/50)
        base_model = LogisticRegression(class_weight=None, max_iter=2000, random_state=42, solver="lbfgs")
        # Исключаем слишком маленькие C (0.001), чтобы избежать схлопывания скоров
        param_grid = {'C': [0.1, 0.5, 1.0, 5.0]}
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        grid = GridSearchCV(base_model, param_grid, cv=cv, scoring='roc_auc', n_jobs=-1)
        grid.fit(X_scaled, y_train)
        
        self.model = grid.best_estimator_
        print(f"[Train] Best C: {self.model.C}")
        
        self.is_trained = True

        # Дата версии
        self.version_date = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")

        # Оценка на train
        y_prob = self.model.predict_proba(X_scaled)[:, 1]
        train_auc = roc_auc_score(y_train, y_prob)
        print(f"[Train] AUC-ROC: {train_auc:.4f}")

        return train_auc

    def _compute_woe(self, df, y):
        """Вычисление WOE и IV для ключевых числовых фичей (бонус)."""
        key_features = ["dti", "pti", "income_cv", "max_delinquency",
                        "summa_daromad_ratio", "ish_staji_oy", "yosh"]

        for feat in key_features:
            try:
                bins = pd.qcut(df[feat], q=5, duplicates="drop")
                ct = pd.crosstab(bins, y)
                if ct.shape[1] < 2:
                    continue
                ct.columns = ["good", "bad"]
                ct["good_pct"] = ct["good"] / ct["good"].sum()
                ct["bad_pct"] = ct["bad"] / ct["bad"].sum()
                # Избегаем деления на ноль
                ct["good_pct"] = ct["good_pct"].replace(0, 0.0001)
                ct["bad_pct"] = ct["bad_pct"].replace(0, 0.0001)
                ct["woe"] = np.log(ct["good_pct"] / ct["bad_pct"])
                ct["iv"] = (ct["good_pct"] - ct["bad_pct"]) * ct["woe"]
                self.woe_bins[feat] = {
                    "iv": ct["iv"].sum(),
                    "bins": ct.to_dict(),
                }
            except Exception:
                pass

    def preprocess(self, X):
        """Применяет Target Encoding и Winsorization."""
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=self.feature_columns)
        else:
            X = X.copy()
            
        target_cols = ["bandlik_encoded", "talim_encoded", "maqsad_encoded"]
        for col in target_cols:
            if col in X.columns and col in self.target_encodings:
                enc = self.target_encodings[col]
                X[col] = X[col].map(enc["means"]).fillna(enc["global_mean"])
                
        for col, (lo, hi) in self.clip_thresholds.items():
            if col in X.columns:
                X[col] = pd.to_numeric(X[col], errors='coerce').clip(lo, hi)
                
        return X

    def predict_pd(self, X):
        """Предсказание PD (probability of default)."""
        if not self.is_trained:
            raise RuntimeError("Модель не обучена. Запустите train().")
        X_proc = self.preprocess(X)
        X_scaled = self.scaler.transform(X_proc.values)
        return self.model.predict_proba(X_scaled)[:, 1]

    def pd_to_score(self, pd_value):
        """Конвертация PD → скоринговый балл (0–1000)."""
        pd_value = np.clip(pd_value, 1e-6, 1 - 1e-6)
        odds = (1 - pd_value) / pd_value
        score = OFFSET + FACTOR * np.log(odds)
        return np.clip(score, 0, 1000).round(0).astype(int)

    def explain_decision(self, features_dict, lang="ru"):
        """Объяснение решения: вклад каждого фактора в баллах."""
        if not self.is_trained:
            raise RuntimeError("Модель не обучена.")

        coefficients = self.model.coef_[0]
        scale = self.scaler.scale_
        mean = self.scaler.mean_
        
        proc_features = self.preprocess(pd.DataFrame([features_dict], columns=self.feature_columns)).iloc[0]

        factors = []
        for i, feat in enumerate(self.feature_columns):
            feat_val_proc = proc_features.get(feat, self.feature_means.get(feat, 0))
            baseline = self.feature_means.get(feat, 0)
            
            raw_contrib = coefficients[i] * (feat_val_proc - baseline) / scale[i]
            points = round(-raw_contrib * FACTOR, 1)

            feat_name = translate(f"feat.{feat}", lang)
            
            raw_val = features_dict.get(feat, feat_val_proc)

            if abs(points) > 0.5:
                direction = "positive" if points > 0 else "negative"
                factors.append({
                    "feature": feat,
                    "feature_name": feat_name,
                    "value": round(raw_val, 4) if isinstance(raw_val, float) else raw_val,
                    "baseline": round(baseline, 4) if isinstance(baseline, float) else baseline,
                    "points": points,
                    "direction": direction,
                })

        factors.sort(key=lambda x: abs(x["points"]), reverse=True)
        return factors

    def generate_reason_text(self, factors, score, decision, lang="ru"):
        """Генерация текстовой причины решения."""
        top_factors = factors[:5]

        if decision == "defolt":
            negative = [f for f in top_factors if f["direction"] == "negative"]
            if negative:
                reasons = [f"{f['feature_name']}: {f['points']:+.0f} {translate('pts', lang)}" for f in negative[:3]]
                return f"{translate('eng.rej.score', lang).format(score=score)} {translate('eng.rej.factors', lang)} {'; '.join(reasons)}"
            return translate('eng.rej.score', lang).format(score=score)
        else:
            return ""

    def generate_client_reasons(self, factors, decision, lang="ru"):
        """Генерация списка понятных причин для клиента."""
        if decision == "toladi":
            return []
            
        reasons = []
        reasons.append(translate('eng.rej.cli.total', lang))
        
        top_negative = [f for f in factors if f["direction"] == "negative"][:3]
        for factor in top_negative:
            fname = factor["feature"]
            if fname == "dti": reasons.append(translate('eng.rej.cli.dti', lang))
            elif fname == "pti": reasons.append(translate('eng.rej.cli.pti', lang))
            elif fname == "summa_daromad_ratio": reasons.append(translate('eng.rej.cli.summa', lang))
            elif fname == "max_delinquency": reasons.append(translate('eng.rej.cli.delinq', lang))
            elif fname == "income_cv": reasons.append(translate('eng.rej.cli.cv', lang))
            elif fname == "bandlik_encoded": reasons.append(translate('eng.rej.cli.emp', lang))
            
        return list(dict.fromkeys(reasons))

    def score_application(self, features_dict, lang="ru"):
        """
        Полная оценка одной заявки.
        Возвращает dict с score, pd, decision, factors, reason, client_reasons.
        """
        X = np.array([[features_dict.get(f, 0) for f in self.feature_columns]], dtype=object)
        pd_val = self.predict_pd(X)[0]
        score = int(self.pd_to_score(np.array([pd_val]))[0])
        decision = "toladi" if score >= SCORE_THRESHOLD else "defolt"
        factors = self.explain_decision(features_dict, lang=lang)
        reason = self.generate_reason_text(factors, score, decision, lang=lang)
        client_reasons = self.generate_client_reasons(factors, decision, lang=lang)

        return {
            "score": score,
            "pd": round(pd_val, 4),
            "decision": decision,
            "decision_label": translate("status.approved", lang) if decision == "toladi" else translate("status.rejected", lang),
            "factors": factors,
            "reason": reason,
            "client_reasons": client_reasons,
            "threshold": SCORE_THRESHOLD,
            "version": self.version,
        }

    def find_max_limit(self, features_dict, min_amount=100000, max_amount=100000000):
        """
        Бонус: Binary search для максимального лимита кредита.
        Ищет максимальную сумму, при которой заявка ещё одобряется.
        """
        if not self.is_trained:
            raise RuntimeError("Модель не обучена.")

        lo, hi = min_amount, max_amount
        best_limit = 0

        # Existing monthly debt burden, independent of the amount being
        # searched. None of the three call sites (apply_form, application_detail,
        # api_whatif) actually put "mavjud_oylik_yuk"/"total_loan_payment" into
        # features_dict -- FEATURE_COLUMNS doesn't include them, so they were
        # silently dropped and every search ran as if the applicant had zero
        # existing debt, inflating the resulting limit. "dti" IS set correctly
        # by every caller as monthly_debt / income, so back the debt amount out
        # of that instead of depending on keys that don't reliably arrive here.
        income_for_dti = features_dict.get("median_income", 1)
        existing_monthly_debt = features_dict.get(
            "mavjud_oylik_yuk", features_dict.get("total_loan_payment", 0)
        ) or (features_dict.get("dti", 0) * max(income_for_dti, 1))

        for _ in range(30):  # ~30 итераций достаточно для точности до 1 сума
            mid = (lo + hi) // 2
            test_features = features_dict.copy()

            # Пересчёт фичей с новой суммой
            declared_income = test_features.get("deklaratsiya_daromad",
                                                 test_features.get("median_income", 1))
            muddat = test_features.get("muddat_oy", 12)
            new_payment = mid / max(muddat, 1)
            test_features["summa_daromad_ratio"] = mid / max(declared_income, 1)
            test_features["new_monthly_payment"] = new_payment
            pti_at_mid = (existing_monthly_debt + new_payment) / max(test_features.get("median_income", 1), 1)
            test_features["pti"] = pti_at_mid

            # Only the approve/reject boundary matters during search -- call
            # predict_pd directly instead of the full score_application(),
            # which would also build explain_decision()'s factor breakdown,
            # translate() every feature name, and render reason/client_reasons
            # text on all 30 iterations for output nothing here ever reads.
            X = np.array([[test_features.get(f, 0) for f in self.feature_columns]], dtype=object)
            score = int(self.pd_to_score(self.predict_pd(X))[0])

            # Hard affordability cap alongside the model's own score -- PTI
            # rising with `mid` while everything else stays fixed means this
            # stays monotonic, so the binary search invariant still holds.
            approved = score >= SCORE_THRESHOLD and pti_at_mid <= MAX_PTI_FOR_LIMIT_SEARCH
            if approved:
                best_limit = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return best_limit

    def evaluate_on_test(self, df=None):
        """Оценка качества на тесте (с ответами)."""
        if df is None:
            df = build_feature_dataset()

        test_df = df[df["target"].isna()].copy()
        answers = load_test_answers()

        X_test = test_df[self.feature_columns].values
        pd_vals = self.predict_pd(X_test)
        scores = self.pd_to_score(pd_vals)

        test_df = test_df.copy()
        test_df["predicted_pd"] = pd_vals
        test_df["score"] = scores
        test_df["predicted_decision"] = ["toladi" if s >= SCORE_THRESHOLD else "defolt" for s in scores]

        # Merge с ответами
        merged = test_df.merge(answers, on="application_id", how="left")

        if "haqiqiy_pd" in merged.columns:
            auc = roc_auc_score(
                merged["haqiqiy_natija"].map({"toladi": 0, "defolt": 1}),
                merged["predicted_pd"]
            )
            gini = 2 * auc - 1
            print(f"[Test] AUC-ROC: {auc:.4f}, Gini: {gini:.4f}")
            return auc, gini, test_df

        return None, None, test_df

    def generate_results_file(self, df=None):
        """Генерация файла natija/kredit_qarorlari.csv."""
        if df is None:
            df = build_feature_dataset()

        test_df = df[df["target"].isna()].copy()
        X_test = test_df[self.feature_columns].values
        pd_vals = self.predict_pd(X_test)
        scores = self.pd_to_score(pd_vals)

        results = []
        for idx, (_, row) in enumerate(test_df.iterrows()):
            features_dict = {f: row[f] for f in self.feature_columns}
            factors = self.explain_decision(features_dict)
            decision = "toladi" if scores[idx] >= SCORE_THRESHOLD else "defolt"
            reason = self.generate_reason_text(factors, scores[idx], decision)

            results.append({
                "application_id": row["application_id"],
                "score": scores[idx],
                "pd": round(pd_vals[idx], 4),
                "decision": decision,
                "sabab": reason,
            })

        os.makedirs(RESULT_DIR, exist_ok=True)
        result_df = pd.DataFrame(results)
        output_path = os.path.join(RESULT_DIR, "kredit_qarorlari.csv")
        result_df.to_csv(output_path, index=False)
        print(f"Результаты сохранены: {output_path} ({len(result_df)} строк)")
        return result_df

    def save_model(self, path=MODEL_PATH):
        """Сохранение модели."""
        data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_means": self.feature_means,
            "woe_bins": self.woe_bins,
            "target_encodings": self.target_encodings,
            "clip_thresholds": self.clip_thresholds,
            "version": self.version,
            "version_date": self.version_date,
            "version_id": self.version_id,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"Модель сохранена: {path}")

    def load_model(self, path=MODEL_PATH):
        """Загрузка модели."""
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_means = data["feature_means"]
        self.woe_bins = data.get("woe_bins", {})
        self.target_encodings = data.get("target_encodings", {})
        self.clip_thresholds = data.get("clip_thresholds", {})
        self.version = data.get("version", "v1.0")
        self.version_date = data.get("version_date", "N/A")
        self.version_id = data.get("version_id")
        self.is_trained = True
        return True

    def publish_version(self, model_path, train_auc=None, test_auc=None, test_gini=None, n_train=None):
        """SCD Type 2: register this trained model as a new scorecard version
        in db.py (closes the previously-active version, never updates it)."""
        import db
        self.version_id = db.publish_scorecard_version(
            model_path=model_path, train_auc=train_auc, test_auc=test_auc,
            test_gini=test_gini, n_train=n_train,
            description=f"LogisticRegression, C={getattr(self.model, 'C', '?')}",
        )
        self.version = f"v{self.version_id}"
        return self.version_id

    def seed_decision_log(self, df):
        """Populate the immutable decisions log with one entry per
        application in the dataset, tagged with this engine's current
        scorecard_version_id. Idempotent at the call-site (app.py/__main__
        check db.has_decisions_for_version() first) -- this method itself
        just does the bulk insert.

        Stores factors as returned by explain_decision(): each item already
        carries the language-agnostic "feature" key alongside a "feature_name"
        that happens to be in whatever `lang` was passed here. Display code
        re-translates "feature" at render time using the viewer's current
        session language, so the stored log is language-agnostic in practice
        even though this call bakes in one language's labels redundantly.
        """
        import db

        if self.version_id is None:
            raise RuntimeError("Engine has no version_id -- call publish_version() first.")

        X_all = df[self.feature_columns].values
        pd_vals = self.predict_pd(X_all)
        scores = self.pd_to_score(pd_vals)

        rows = []
        for idx, (_, row) in enumerate(df.iterrows()):
            features_dict = {f: row[f] for f in self.feature_columns}
            factors = self.explain_decision(features_dict, lang="ru")
            decision = "toladi" if scores[idx] >= SCORE_THRESHOLD else "defolt"
            rows.append({
                "application_id": row["application_id"],
                "applicant_id": row.get("applicant_id"),
                "scorecard_version_id": self.version_id,
                "score": int(scores[idx]),
                "pd": round(float(pd_vals[idx]), 4),
                "decision": decision,
                "threshold": SCORE_THRESHOLD,
                "source": "dataset",
                "factors_json": json.dumps(factors, ensure_ascii=False),
                "input_snapshot_json": json.dumps(features_dict, ensure_ascii=False, default=str),
            })

        db.insert_decisions_bulk(rows)
        print(f"Immutable decision log: seeded {len(rows)} rows for scorecard_version_id={self.version_id}")

    def get_model_info(self, lang="ru"):
        """Информация о модели для UI."""
        if not self.is_trained:
            return {"status": "not_trained"}

        coefs = dict(zip(self.feature_columns, self.model.coef_[0]))
        sorted_coefs = sorted(coefs.items(), key=lambda x: abs(x[1]), reverse=True)

        iv_info = {}
        for feat, data in self.woe_bins.items():
            iv_info[feat] = round(data["iv"], 4)

        all_coefs = []
        for f, c in sorted_coefs:
            raw_contrib = c / self.scaler.scale_[self.feature_columns.index(f)]
            points_change = round(-raw_contrib * FACTOR, 1)
            all_coefs.append({
                "feature": translate(f"feat.{f}", lang), 
                "coefficient": round(c, 4),
                "points_change": points_change
            })

        return {
            "status": "trained",
            "version": self.version,
            "version_date": self.version_date,
            "n_features": len(self.feature_columns),
            "all_coefficients": all_coefs,
            "intercept": round(self.model.intercept_[0], 4),
            "iv_values": {
                translate(f"feat.{f}", lang): v
                for f, v in sorted(iv_info.items(), key=lambda x: x[1], reverse=True)
            },
            "threshold": SCORE_THRESHOLD,
            "max_pti_for_limit_search": MAX_PTI_FOR_LIMIT_SEARCH,
            "base_score": BASE_SCORE,
            "pdo": PDO,
            "base_odds": BASE_ODDS,
            "factor": round(FACTOR, 4),
            "offset": round(OFFSET, 4),
            "feature_means": {
                translate(f"feat.{f}", lang): round(v, 4)
                for f, v in self.feature_means.items()
            }
        }


# Глобальный экземпляр
engine = CreditScoringEngine()

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


def train_publish_and_seed(eng, df):
    """Full pipeline for one scorecard version: train -> evaluate -> publish
    (SCD Type 2) -> save the versioned model file -> seed the immutable
    decision log for every application in the dataset. Shared by __main__
    (build time) and get_engine()'s fallback (runtime safety net)."""
    import db
    db.init_db()

    train_auc = eng.train(df)
    test_auc, gini, test_df = eng.evaluate_on_test(df)

    os.makedirs(MODELS_DIR, exist_ok=True)
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    versioned_path = os.path.join(MODELS_DIR, f"model_{timestamp}.pkl")

    eng.publish_version(
        model_path=versioned_path, train_auc=train_auc, test_auc=test_auc,
        test_gini=gini, n_train=int(df["target"].notna().sum()),
    )
    eng.save_model(versioned_path)
    eng.save_model()  # also refresh the canonical model.pkl the app loads by default

    eng.generate_results_file(df)
    eng.seed_decision_log(df)

    return train_auc, test_auc, gini, test_df


def get_engine():
    """Получить готовый движок (обучить если нужно)."""
    if not engine.is_trained:
        if not engine.load_model():
            df = build_feature_dataset()
            train_publish_and_seed(engine, df)
    return engine


if __name__ == "__main__":
    print("=" * 60)
    print("Credit Scoring Engine — Обучение и оценка")
    print("=" * 60)

    df = build_feature_dataset()
    eng = CreditScoringEngine()

    train_auc, test_auc, gini, test_df = train_publish_and_seed(eng, df)
    print(f"[Version] Published scorecard_version_id={eng.version_id} -> {eng.version}")

    # Информация о модели
    info = eng.get_model_info()
    print(f"\nAll coefficients:")
    for c in info["all_coefficients"]:
        print(f"  {c['feature']}: {c['coefficient']}")

    print(f"\nIV values:")
    for f, v in info["iv_values"].items():
        print(f"  {f}: {v}")

    # Пример скоринга
    print("\n" + "=" * 60)
    print("Пример скоринга первой тестовой заявки:")
    sample = test_df.iloc[0]
    features = {f: sample[f] for f in FEATURE_COLUMNS}
    result = eng.score_application(features)
    print(f"  Score: {result['score']}")
    print(f"  PD: {result['pd']}")
    print(f"  Decision: {result['decision_label']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Top factors:")
    for f in result["factors"][:5]:
        print(f"    {f['feature_name']}: {f['points']:+.1f} pts (value={f['value']}, baseline={f['baseline']})")
