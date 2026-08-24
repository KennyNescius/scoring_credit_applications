"""
app.py — Flask веб-приложение для кредитного скоринга.
Маршруты:
  / — Главная (список заявок + статистика)
  /apply — Форма подачи заявки (клиентская сторона)
  /underwriter — Панель андеррайтера (банковская сторона)
  /underwriter/<app_id> — Детали заявки
  /whatif — What-if симулятор (бонус)
  /api/whatif — API для симулятора
  /model-info — Информация о модели
"""

import os
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import db
from data_loader import build_feature_dataset, FEATURE_COLUMNS
from scoring_engine import get_engine, SCORE_THRESHOLD, DEFAULT_AFFORDABILITY_CAP_ENABLED, DEFAULT_MAX_PTI_FOR_LIMIT_SEARCH
from translations import translate

db.init_db()

app = Flask(__name__)
# Fixed, not os.urandom(24): with multiple gunicorn workers (no --preload),
# each worker process re-executes this module independently, so a random
# key here gives every worker a DIFFERENT secret. A session cookie signed
# by worker A then fails validation on worker B, silently resetting
# session['lang'] back to the default -- this was reproducible (~50% of
# requests) and is exactly why the language toggle looked flaky.
app.secret_key = os.environ.get("SECRET_KEY", "cbu-hackathon-2026-credit-scoring-dev-key")

@app.context_processor
def inject_translator():
    lang = session.get('lang', 'ru')
    return dict(t=lambda key: translate(key, lang), current_lang=lang)

@app.route("/set_lang/<lang>")
def set_lang(lang):
    if lang in ["ru", "uz"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for('index'))

# Raw dataset values -> translation keys, for fields displayed as free text
# (not already run through a select/option list, which templates translate
# inline). Without these, the table/detail screens showed the CSV's raw
# Uzbek codes ("iste'mol", "xususiy", "M"...) even in Russian mode.
PURPOSE_KEYS = {"ipoteka": "f.purpose.mortgage", "avto": "f.purpose.auto",
                "iste'mol": "f.purpose.consum", "kredit_karta": "f.purpose.card"}
OUTCOME_KEYS = {"toladi": "outcome.toladi", "defolt": "outcome.defolt"}
GENDER_KEYS = {"M": "f.gender.m", "F": "f.gender.f"}
EMPLOYMENT_KEYS = {"xususiy": "f.employment.priv", "byudjet": "f.employment.gov",
                    "IT": "f.employment.it", "savdo": "f.employment.trade",
                    "qurilish": "f.employment.construct", "transport": "f.employment.trans",
                    "o'z_ishi": "f.employment.self", "ishsiz": "f.employment.unemp"}
EDUCATION_KEYS = {"oliy": "f.edu.higher", "orta": "f.edu.mid"}


def tr_lookup(mapping, raw, lang, default="—"):
    """Translate a raw dataset value via `mapping`; falls through to the raw
    value itself (not `default`) if it's simply not one of the known codes,
    so unexpected data doesn't get hidden -- `default` only covers None/empty.
    Test-split rows have a real NaN (not None/"") in `natija`; pd.isna()
    catches that -- `raw == ""` alone lets it through, since NaN != NaN and
    NaN == "" are both False, and Jinja then renders it as the literal
    string "nan"."""
    if raw is None or raw == "" or pd.isna(raw):
        return default
    key = mapping.get(raw)
    if key:
        return translate(key, lang)
    if raw == "orta_maxsus":  # composite: same convention used in the <select> options
        return f"{translate('f.edu.mid', lang)} {translate('f.edu.special', lang)}"
    return raw


def get_affordability_settings():
    """Toggleable/adjustable affordability cap on find_max_limit() -- our
    own addition on top of the bonus limit-search algorithm, not part of
    the ToR. Off by default (matches DEFAULT_AFFORDABILITY_CAP_ENABLED);
    persisted in db.py's settings table so a change on /model-info sticks
    across requests/workers. Returns (enabled: bool, cap: float)."""
    enabled = db.get_setting("affordability_cap_enabled", str(int(DEFAULT_AFFORDABILITY_CAP_ENABLED))) == "1"
    cap = float(db.get_setting("affordability_cap_pti", str(DEFAULT_MAX_PTI_FOR_LIMIT_SEARCH)))
    return enabled, cap


def get_pti_cap():
    """None when the cap is off -- find_max_limit()'s own default, so
    callers that forget this helper still get the score-only behavior."""
    enabled, cap = get_affordability_settings()
    return cap if enabled else None


# Загрузка данных и модели при старте
_df = None
_engine = None


def get_data():
    global _df
    if _df is None:
        _df = build_feature_dataset()
    return _df


def get_scoring_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


@app.route("/")
def index():
    """Главная страница — обзор."""
    engine = get_scoring_engine()
    df = get_data()

    train = df[df["target"].notna()]
    test = df[df["target"].isna()]

    # Подготовка данных для графиков
    X_all = df[FEATURE_COLUMNS].values
    pd_vals = engine.predict_pd(X_all)
    scores = engine.pd_to_score(pd_vals)

    approved_count = int((scores >= SCORE_THRESHOLD).sum())
    rejected_count = int((scores < SCORE_THRESHOLD).sum())
    lang = session.get('lang', 'ru')

    bins = np.arange(0, 1050, 50)
    hist, _ = np.histogram(scores, bins=bins)
    score_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]
    score_data = hist.tolist()

    rejected_idx = np.where(scores < SCORE_THRESHOLD)[0]
    if len(rejected_idx) > 0:
        X_rej_raw = X_all[rejected_idx]
        X_rej_proc = engine.preprocess(pd.DataFrame(X_rej_raw, columns=FEATURE_COLUMNS))
        X_rej = engine.scaler.transform(X_rej_proc.values)
        # Отрицательный вектор raw_contrib - это вклад в баллы
        # Находим наименьший вклад (наиболее негативный) по каждой заявке
        points = -(engine.model.coef_[0] * X_rej)
        worst_features_idx = np.argmin(points, axis=1)
        reason_series = pd.Series(worst_features_idx).map({i: translate(f"feat.{f}", lang) for i, f in enumerate(FEATURE_COLUMNS)})
        reason_counts = reason_series.value_counts().head(5)
        reasons_labels = reason_counts.index.tolist()
        reasons_data = reason_counts.values.tolist()
    else:
        reasons_labels = []
        reasons_data = []

    chart_data = {
        "approval": {
            "labels": [translate("uw.stat.appr", lang), translate("uw.stat.rej", lang)],
            "data": [approved_count, rejected_count],
        },
        "scores": {"labels": score_labels, "data": score_data},
        "reasons": {"labels": reasons_labels, "data": reasons_data}
    }

    stats = {
        "total_applications": len(df),
        "train_count": len(train),
        "test_count": len(test),
        "default_rate": f"{train['target'].mean() * 100:.1f}%",
        "model_version": engine.version,
        "model_date": engine.version_date,
        "threshold": SCORE_THRESHOLD,
    }

    return render_template("index.html", stats=stats, chart_data=json.dumps(chart_data))


@app.route("/apply", methods=["GET", "POST"])
def apply_form():
    """Клиентская форма подачи заявки."""
    engine = get_scoring_engine()
    result = None

    if request.method == "POST":
        try:
            # Получаем данные из формы
            form_data = {
                "yosh": int(request.form.get("yosh", 30)),
                "ish_staji_oy": int(request.form.get("ish_staji_oy", 12)),
                "deklaratsiya_daromad": float(request.form.get("deklaratsiya_daromad", 3000000)),
                "oila_azolari": int(request.form.get("oila_azolari", 3)),
                "mijoz_boldi_oy": int(request.form.get("mijoz_boldi_oy", 12)),
                "sorlgan_summa": float(request.form.get("sorlgan_summa", 10000000)),
                "muddat_oy": int(request.form.get("muddat_oy", 12)),
                "mavjud_oylik_yuk": float(request.form.get("mavjud_oylik_yuk", 0)),
            }

            bandlik = request.form.get("bandlik", "xususiy")
            talim = request.form.get("talim", "oliy")
            maqsad = request.form.get("maqsad", "iste'mol")

            # Оценка median_income на основе деklaratsiya_daromad
            median_income = form_data["deklaratsiya_daromad"]

            # Вычисление фичей
            features = {
                "yosh": form_data["yosh"],
                "ish_staji_oy": form_data["ish_staji_oy"],
                "oila_azolari": form_data["oila_azolari"],
                "mijoz_boldi_oy": form_data["mijoz_boldi_oy"],
                "bandlik_encoded": bandlik,
                "talim_encoded": talim,
                "maqsad_encoded": maqsad,
                "muddat_oy": form_data["muddat_oy"],
                "median_income": median_income,
                "income_cv": 0.15,
                "max_delinquency": 0,
            }

            new_payment = form_data["sorlgan_summa"] / max(form_data["muddat_oy"], 1)
            monthly_debt = form_data["mavjud_oylik_yuk"]
            features["dti"] = monthly_debt / max(median_income, 1)
            features["pti"] = (monthly_debt + new_payment) / max(median_income, 1)
            features["summa_daromad_ratio"] = form_data["sorlgan_summa"] / max(form_data["deklaratsiya_daromad"], 1)

            lang = session.get('lang', 'ru')
            result = engine.score_application(features, lang=lang)
            result["form_data"] = form_data
            result["bandlik"] = bandlik
            result["talim"] = talim
            result["maqsad"] = maqsad

            # Лимит поиск (бонус)
            features["deklaratsiya_daromad"] = form_data["deklaratsiya_daromad"]
            max_limit = engine.find_max_limit(features, pti_cap=get_pti_cap())
            result["max_limit"] = f"{max_limit:,.0f}"

            # Immutable decision log: every manually submitted application
            # gets its own append-only entry, tagged with the scorecard
            # version that actually made the decision.
            application_id = f"WEB-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S%f')}"
            db.insert_decision(
                application_id=application_id, applicant_id=None,
                scorecard_version_id=engine.version_id, score=result["score"],
                pd_value=result["pd"], decision=result["decision"],
                threshold=result["threshold"], factors=result["factors"],
                input_snapshot=features, source="web_form",
            )
            result["application_id"] = application_id

        except Exception as e:
            result = {"error": str(e)}

    return render_template("application_form.html", result=result)


@app.route("/underwriter")
def underwriter():
    """Панель андеррайтера — все заявки. Источник данных — immutable
    decision log (db.py), а не пересчёт вживую: то, что видит андеррайтер,
    это реально сохранённые решения, а не мгновенный снимок модели."""
    df = get_data()

    # Параметры фильтрации
    filter_type = request.args.get("filter", "all")  # all, train, test
    filter_decision = request.args.get("decision", "all")  # all, toladi, defolt
    page = int(request.args.get("page", 1))
    per_page = 25

    decisions = db.list_latest_decisions()
    dec_df = pd.DataFrame([{
        "application_id": d["application_id"],
        "score": d["score"],
        "pd_predicted": d["pd"],
        "decision_predicted": d["decision"],
    } for d in decisions])

    # web_form-заявки (application_id "WEB-...") не входят в датасет -- их
    # нет смысла показывать в "портфельной" очереди по существующим заявкам.
    df_scored = df.merge(dec_df, on="application_id", how="inner")

    # Фильтрация
    if filter_type == "train":
        df_scored = df_scored[df_scored["target"].notna()]
    elif filter_type == "test":
        df_scored = df_scored[df_scored["target"].isna()]

    if filter_decision == "toladi":
        df_scored = df_scored[df_scored["decision_predicted"] == "toladi"]
    elif filter_decision == "defolt":
        df_scored = df_scored[df_scored["decision_predicted"] == "defolt"]

    # Сортировка по скору
    df_scored = df_scored.sort_values("score", ascending=True)

    total = len(df_scored)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_data = df_scored.iloc[start:end]

    lang = session.get('lang', 'ru')

    applications = []
    for _, row in page_data.iterrows():
        natija_raw = row.get("natija")
        applications.append({
            "application_id": row["application_id"],
            "applicant_id": row["applicant_id"],
            "ism": row.get("ism", "N/A"),
            "score": int(row["score"]),
            "pd": round(row["pd_predicted"], 4),
            "decision": row["decision_predicted"],
            "actual": tr_lookup(OUTCOME_KEYS, natija_raw, lang),
            "actual_raw": natija_raw if natija_raw in OUTCOME_KEYS else "unknown",
            "amount": f"{row['sorlgan_summa']:,.0f}",
            "purpose": tr_lookup(PURPOSE_KEYS, row.get("maqsad"), lang),
            "income": f"{row.get('deklaratsiya_daromad', 0):,.0f}",
            "dti": round(row.get("dti", 0), 2),
        })

    # Статистика (считаем на основе отфильтрованного df_scored)
    filtered_scores = df_scored["score"].values
    approved_count = int((filtered_scores >= SCORE_THRESHOLD).sum())
    rejected_count = int((filtered_scores < SCORE_THRESHOLD).sum())

    stats = {
        "total": total,
        "approved": approved_count,
        "rejected": rejected_count,
        "approved_pct": f"{approved_count / total * 100:.1f}%" if total > 0 else "0%",
        "rejected_pct": f"{rejected_count / total * 100:.1f}%" if total > 0 else "0%",
        "avg_score": int(np.mean(filtered_scores)) if len(filtered_scores) > 0 else 0,
        "median_score": int(np.median(filtered_scores)) if len(filtered_scores) > 0 else 0,
    }

    return render_template(
        "underwriter.html",
        applications=applications,
        stats=stats,
        page=page,
        total_pages=total_pages,
        filter_type=filter_type,
        filter_decision=filter_decision,
        threshold=SCORE_THRESHOLD,
        lang=session.get('lang', 'ru')
    )


@app.route("/underwriter/<app_id>")
def application_detail(app_id):
    """Детали конкретной заявки. Score/PD/decision/factors читаются из
    immutable decision log (db.py), а не пересчитываются -- то, что видно
    здесь, это то, что реально было решено, а не текущее состояние модели.
    Человекочитаемый текст (feature_name/reason/client_reasons) при этом
    генерируется заново в языке текущей сессии из замороженных, но
    языконезависимых данных (feature-ключ, points, direction)."""
    engine = get_scoring_engine()
    df = get_data()

    row = df[df["application_id"] == app_id]
    if row.empty:
        return translate("app.not_found", session.get('lang', 'ru')), 404

    row = row.iloc[0]
    features = {f: row[f] for f in FEATURE_COLUMNS}
    lang = session.get('lang', 'ru')

    log_row = db.get_latest_decision_for_application(app_id)
    if log_row is None:
        # Defensive fallback -- shouldn't happen since the whole dataset is
        # seeded at build time, but self-heal by computing and persisting
        # rather than silently leaving this application unlogged.
        result = engine.score_application(features, lang=lang)
        db.insert_decision(
            application_id=app_id, applicant_id=row.get("applicant_id"),
            scorecard_version_id=engine.version_id, score=result["score"],
            pd_value=result["pd"], decision=result["decision"],
            threshold=result["threshold"], factors=result["factors"],
            input_snapshot=features, source="dataset",
        )
        log_row = dict(db.get_latest_decision_for_application(app_id))
    else:
        log_row = dict(log_row)
        stored_factors = json.loads(log_row["factors_json"])
        factors = [
            dict(f, feature_name=translate(f"feat.{f['feature']}", lang))
            for f in stored_factors
        ]
        score = log_row["score"]
        decision = log_row["decision"]
        result = {
            "score": score,
            "pd": log_row["pd"],
            "decision": decision,
            "decision_label": translate("status.approved", lang) if decision == "toladi" else translate("status.rejected", lang),
            "factors": factors,
            "reason": engine.generate_reason_text(factors, score, decision, lang=lang),
            "client_reasons": engine.generate_client_reasons(factors, decision, lang=lang),
            "threshold": log_row["threshold"],
            "version": f"v{log_row['scorecard_version_id']}",
        }

    # Дополнительные данные заявки
    natija_raw = row.get("natija")
    app_info = {
        "application_id": row["application_id"],
        "applicant_id": row["applicant_id"],
        "ism": row.get("ism", "N/A"),
        "yosh": row.get("yosh", "N/A"),
        "jins": tr_lookup(GENDER_KEYS, row.get("jins"), lang, default="N/A"),
        "viloyat": row.get("viloyat", "N/A"),
        "bandlik": tr_lookup(EMPLOYMENT_KEYS, row.get("bandlik"), lang, default="N/A"),
        "talim": tr_lookup(EDUCATION_KEYS, row.get("talim"), lang, default="N/A"),
        "ish_staji_oy": row.get("ish_staji_oy", 0),
        "deklaratsiya_daromad": f"{row.get('deklaratsiya_daromad', 0):,.0f}",
        "oila_azolari": row.get("oila_azolari", 0),
        "sorlgan_summa": f"{row.get('sorlgan_summa', 0):,.0f}",
        "maqsad": tr_lookup(PURPOSE_KEYS, row.get("maqsad"), lang, default="N/A"),
        "muddat_oy": row.get("muddat_oy", 0),
        "actual": tr_lookup(OUTCOME_KEYS, natija_raw, lang),
        "actual_raw": natija_raw if natija_raw in OUTCOME_KEYS else "unknown",
        "median_income": f"{row.get('median_income', 0):,.0f}",
        "income_cv": round(row.get("income_cv", 0), 4),
        "dti": round(row.get("dti", 0), 4),
        "pti": round(row.get("pti", 0), 4),
        "max_delinquency": row.get("max_delinquency", 0),
        "loan_count": row.get("loan_count", 0),
    }

    # Лимит
    features["deklaratsiya_daromad"] = row.get("deklaratsiya_daromad", 0)
    max_limit = engine.find_max_limit(features, pti_cap=get_pti_cap())

    return render_template(
        "application_detail.html",
        app_info=app_info,
        result=result,
        max_limit=f"{max_limit:,.0f}",
        log_entry=log_row,
        lang=lang
    )


@app.route("/whatif")
def whatif():
    """What-if симулятор."""
    return render_template("whatif.html", lang=session.get('lang', 'ru'))


@app.route("/api/whatif", methods=["POST"])
def api_whatif():
    """API для what-if симулятора."""
    engine = get_scoring_engine()

    try:
        data = request.get_json()

        median_income = float(data.get("income", 3000000))
        sorlgan_summa = float(data.get("amount", 10000000))
        muddat = int(data.get("term", 12))
        mavjud_yuk = float(data.get("existing_payments", 0))
        new_payment = sorlgan_summa / max(muddat, 1)

        features = {
            "yosh": int(data.get("age", 30)),
            "ish_staji_oy": int(data.get("experience", 24)),
            "oila_azolari": int(data.get("family", 3)),
            "mijoz_boldi_oy": int(data.get("client_months", 12)),
            "bandlik_encoded": data.get("employment", "xususiy"),
            "talim_encoded": data.get("education", "oliy"),
            "maqsad_encoded": data.get("purpose", "iste'mol"),
            "muddat_oy": muddat,
            "median_income": median_income,
            "income_cv": float(data.get("income_cv", 0.15)),
            "max_delinquency": int(data.get("max_delinquency", 0)),
            "dti": mavjud_yuk / max(median_income, 1),
            "pti": (mavjud_yuk + new_payment) / max(median_income, 1),
            "summa_daromad_ratio": sorlgan_summa / max(median_income, 1),
        }

        lang = session.get('lang', 'ru')
        result = engine.score_application(features, lang=lang)

        # Лимит
        features["deklaratsiya_daromad"] = median_income
        max_limit = engine.find_max_limit(features, pti_cap=get_pti_cap())
        result["max_limit"] = max_limit

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/model-info")
def model_info():
    """Информация о модели."""
    engine = get_scoring_engine()
    info = engine.get_model_info(lang=session.get('lang', 'ru'))
    enabled, cap = get_affordability_settings()
    return render_template(
        "model_info.html", info=info, lang=session.get('lang', 'ru'),
        affordability_enabled=enabled, affordability_cap_pct=round(cap * 100),
    )


@app.route("/model-info/affordability", methods=["POST"])
def update_affordability_settings():
    """Toggle/adjust the affordability cap (db.py settings, global -- see
    get_affordability_settings()). Not a ToR requirement; our own addition
    on top of the find_max_limit bonus algorithm."""
    enabled = request.form.get("enabled") == "on"
    try:
        pct = float(request.form.get("cap_pct", DEFAULT_MAX_PTI_FOR_LIMIT_SEARCH * 100))
    except ValueError:
        pct = DEFAULT_MAX_PTI_FOR_LIMIT_SEARCH * 100
    pct = min(max(pct, 1), 100)  # keep it a sane percentage
    db.set_setting("affordability_cap_enabled", "1" if enabled else "0")
    db.set_setting("affordability_cap_pti", pct / 100)
    return redirect(url_for('model_info'))

@app.route("/erd")
def erd_diagram():
    """Схема базы данных (ERD)."""
    return render_template("erd.html", lang=session.get('lang', 'ru'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
