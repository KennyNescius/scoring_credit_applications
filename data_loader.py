"""
data_loader.py — Загрузка и объединение всех CSV-файлов датасета.
Результат: единый DataFrame с фичами для каждой заявки.
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a2_credit")


def load_applicants(data_dir=DATA_DIR):
    """Загрузка данных заявителей."""
    df = pd.read_csv(os.path.join(data_dir, "applicants.csv"))
    return df


def load_applications(data_dir=DATA_DIR):
    """Загрузка заявок (train + test)."""
    df = pd.read_csv(os.path.join(data_dir, "applications.csv"))
    return df


def load_monthly_flows(data_dir=DATA_DIR):
    """Загрузка помесячных транзакций."""
    df = pd.read_csv(os.path.join(data_dir, "monthly_flows.csv"))
    return df


def load_existing_loans(data_dir=DATA_DIR):
    """Загрузка существующих кредитов."""
    df = pd.read_csv(os.path.join(data_dir, "existing_loans.csv"))
    return df


def load_test_answers(data_dir=DATA_DIR):
    """Загрузка ответов для тестовых заявок."""
    df = pd.read_csv(os.path.join(data_dir, "test_natijalari.csv"))
    return df


def aggregate_monthly_flows(flows_df):
    """
    Агрегация помесячных транзакций по каждому заявителю:
    - median_income: медианный доход
    - mean_income: средний доход
    - income_std: стандартное отклонение дохода
    - income_cv: коэффициент вариации (CV) = std / mean
    - avg_expense_ratio: средний расход / доход
    - avg_naqd_ratio: среднее снятие наличных / доход
    - avg_balance: средний остаток на конец месяца
    - min_balance: минимальный остаток
    """
    agg = flows_df.groupby("applicant_id").agg(
        median_income=("kirim", "median"),
        mean_income=("kirim", "mean"),
        income_std=("kirim", "std"),
        total_income=("kirim", "sum"),
        mean_expense=("chiqim", "mean"),
        mean_naqd=("naqd_yechish", "mean"),
        avg_balance=("oy_oxiri_qoldiq", "mean"),
        min_balance=("oy_oxiri_qoldiq", "min"),
    ).reset_index()

    # Коэффициент вариации дохода (чем выше — тем нестабильнее)
    agg["income_cv"] = agg["income_std"] / agg["mean_income"].replace(0, np.nan)
    agg["income_cv"] = agg["income_cv"].fillna(0)

    # Доля расходов от дохода
    agg["avg_expense_ratio"] = agg["mean_expense"] / agg["mean_income"].replace(0, np.nan)
    agg["avg_expense_ratio"] = agg["avg_expense_ratio"].fillna(1)

    # Доля снятия наличных от дохода
    agg["avg_naqd_ratio"] = agg["mean_naqd"] / agg["mean_income"].replace(0, np.nan)
    agg["avg_naqd_ratio"] = agg["avg_naqd_ratio"].fillna(0)

    return agg


def aggregate_existing_loans(loans_df):
    """
    Агрегация существующих кредитов по заявителю:
    - total_loan_payment: суммарный ежемесячный платёж
    - total_loan_balance: суммарный остаток по кредитам
    - max_delinquency: максимальная просрочка (дней)
    - loan_count: количество активных кредитов
    - has_delinquency: есть ли просрочки > 0
    """
    agg = loans_df.groupby("applicant_id").agg(
        total_loan_payment=("oylik_tolov", "sum"),
        total_loan_balance=("qoldiq", "sum"),
        max_delinquency=("max_kechikish_kun", "max"),
        loan_count=("loan_id", "count"),
    ).reset_index()

    agg["has_delinquency"] = (agg["max_delinquency"] > 0).astype(int)

    return agg


def build_feature_dataset(data_dir=DATA_DIR):
    """
    Собирает полный датасет с фичами для всех заявок.
    Возвращает (full_df, feature_columns, target_column).
    """
    applicants = load_applicants(data_dir)
    applications = load_applications(data_dir)
    flows = load_monthly_flows(data_dir)
    loans = load_existing_loans(data_dir)

    # Агрегация
    flow_agg = aggregate_monthly_flows(flows)
    loan_agg = aggregate_existing_loans(loans)

    # Объединение: applications → applicants → flows → loans
    df = applications.merge(applicants, on="applicant_id", how="left")
    df = df.merge(flow_agg, on="applicant_id", how="left")
    df = df.merge(loan_agg, on="applicant_id", how="left")

    # Заполнение пропусков для тех, у кого нет кредитов
    loan_cols = ["total_loan_payment", "total_loan_balance", "max_delinquency",
                 "loan_count", "has_delinquency"]
    for col in loan_cols:
        df[col] = df[col].fillna(0)

    # ===== Производные фичи =====

    # DTI (Debt-to-Income): (текущая нагрузка + платежи по существующим кредитам) / доход
    monthly_debt = df["mavjud_oylik_yuk"] + df["total_loan_payment"]
    monthly_income = df["median_income"].replace(0, np.nan)
    df["dti"] = monthly_debt / monthly_income
    df["dti"] = df["dti"].fillna(1.0).clip(0, 5)

    # Отношение запрошенной суммы к декларируемому доходу
    df["summa_daromad_ratio"] = df["sorlgan_summa"] / df["deklaratsiya_daromad"].replace(0, np.nan)
    df["summa_daromad_ratio"] = df["summa_daromad_ratio"].fillna(10).clip(0, 50)

    # Ежемесячный платёж по новому кредиту (простое приближение)
    df["new_monthly_payment"] = df["sorlgan_summa"] / df["muddat_oy"].replace(0, 1)

    # PTI (Payment-to-Income): (все платежи + новый) / доход
    total_payments = monthly_debt + df["new_monthly_payment"]
    df["pti"] = total_payments / monthly_income
    df["pti"] = df["pti"].fillna(1.0).clip(0, 5)

    # Оставляем исходные строковые категории. Энкодинг(Target Mean) будет в scoring_engine!
    df["bandlik_encoded"] = df["bandlik"].fillna("xususiy")
    df["talim_encoded"] = df["talim"].fillna("oliy")
    df["maqsad_encoded"] = df["maqsad"].fillna("iste'mol")

    # Таргет
    df["target"] = df["natija"].map({"toladi": 0, "defolt": 1})

    return df


# Список фичей для модели
FEATURE_COLUMNS = [
    "yosh",
    "ish_staji_oy",
    "oila_azolari",
    "bandlik_encoded",
    "talim_encoded",
    "muddat_oy",
    "dti",
    "pti",
    "summa_daromad_ratio",
    "income_cv",
    "median_income",
    "max_delinquency",
]

# Человекочитаемые имена фичей (для объяснений)
FEATURE_NAMES_RU = {
    "yosh": "Возраст",
    "ish_staji_oy": "Стаж работы (мес)",
    "oila_azolari": "Членов семьи",
    "mijoz_boldi_oy": "Срок клиента (мес)",
    "bandlik_encoded": "Тип занятости",
    "talim_encoded": "Образование",
    "maqsad_encoded": "Цель кредита",
    "muddat_oy": "Срок кредита (мес)",
    "dti": "DTI (долг/доход)",
    "pti": "PTI (платёж/доход)",
    "summa_daromad_ratio": "Сумма/Доход",
    "income_cv": "Нестабильность дохода (CV)",
    "avg_expense_ratio": "Доля расходов",
    "avg_naqd_ratio": "Доля снятия наличных",
    "median_income": "Медианный доход",
    "avg_balance": "Средний остаток",
    "min_balance": "Мин. остаток",
    "total_loan_payment": "Платежи по кредитам",
    "max_delinquency": "Макс. просрочка (дн)",
    "loan_count": "Кол-во кредитов",
    "has_delinquency": "Наличие просрочек",
}


if __name__ == "__main__":
    df = build_feature_dataset()
    print(f"Total rows: {len(df)}")
    print(f"Train: {df['target'].notna().sum()}, Test: {df['target'].isna().sum()}")
    print(f"\nFeature stats:")
    print(df[FEATURE_COLUMNS].describe().round(2))
