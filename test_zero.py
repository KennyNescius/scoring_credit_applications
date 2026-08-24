import numpy as np
import pandas as pd
from data_loader import build_feature_dataset, FEATURE_COLUMNS, FEATURE_NAMES_RU
from scoring_engine import get_engine, SCORE_THRESHOLD

print("Loading dataset...")
df = build_feature_dataset()
print("Loading engine...")
engine = get_engine()

print('=' * 70)
print('ТЕСТ 1: Идеальный заявитель (0 кредитов, хороший доход, стаж)')
print('=' * 70)

ideal = {
    'yosh': 35,
    'ish_staji_oy': 120,          # 10 лет стажа
    'oila_azolari': 3,
    'mijoz_boldi_oy': 48,         # 4 года клиент
    'bandlik_encoded': 1,          # IT
    'talim_encoded': 0,            # высшее
    'maqsad_encoded': 2,           # потреб
    'muddat_oy': 12,
    'median_income': 5000000,
    'avg_balance': 1000000,
    'min_balance': 200000,
    'income_cv': 0.1,              # стабильный доход
    'avg_expense_ratio': 0.5,
    'avg_naqd_ratio': 0.2,
    'total_loan_payment': 0,       # нет кредитов
    'max_delinquency': 0,
    'loan_count': 0,               # 0 кредитов
    'has_delinquency': 0,
    'dti': 0.0,                    # нет долгов
    'pti': 0.0,                    # пока без нового кредита
    'summa_daromad_ratio': 4.0,
}
# Добавим PTI от нового кредита
sorlgan = 20000000
ideal['pti'] = (sorlgan / 12) / 5000000  # ~0.33
ideal['summa_daromad_ratio'] = sorlgan / 5000000  # 4.0

result = engine.score_application(ideal)
print(f'Score: {result["score"]}  |  PD: {result["pd"]:.4f}  |  Decision: {result["decision_label"]}')
print(f'Reason: {result["reason"]}')
print()
print("Top factors:")
for f in result['factors'][:10]:
    print(f'  {f["feature_name"]:30s}  {f["points"]:+7.1f} б.  (value={f["value"]}, baseline={f["baseline"]:.4f})')

print()
print('=' * 70)
print('ТЕСТ 2: Коэффициенты модели')
print('=' * 70)
coefs = dict(zip(FEATURE_COLUMNS, engine.model.coef_[0]))
for feat in sorted(coefs, key=lambda x: abs(coefs[x]), reverse=True):
    name = FEATURE_NAMES_RU.get(feat, feat)
    c = coefs[feat]
    mean = engine.feature_means[feat]
    print(f'  {name:35s}  coef={c:+.4f}  mean={mean:.4f}')

print()
print('=' * 70)
print('ТЕСТ 3: Влияние loan_count в данных')
print('=' * 70)
train = df[df['target'].notna()]
print('Средний таргет (доля дефолтов) в зависимости от loan_count:')
for cnt in sorted(train['loan_count'].unique()):
    subset = train[train['loan_count'] == cnt]
    rate = subset['target'].mean()
    print(f'  loan_count={int(cnt)}: дефолт={rate*100:5.1f}% (заявок={len(subset)})')
