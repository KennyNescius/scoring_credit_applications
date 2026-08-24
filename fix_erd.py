import os

extra = {
    "erd.head_title": {"ru": "Архитектура Данных (ERD)", "uz": "Ma'lumotlar arxitekturasi (ERD)"},
    "erd.loan_suffix": {"ru": "кредита", "uz": "kredit"},
    "erd.term": {"ru": "Срок", "uz": "Muddat"},
    "erd.median_inc": {"ru": "Медианный доход", "uz": "Median daromad"},
    "erd.for_12_mo": {"ru": "за 12 {{ t('det.months') }}яцев", "uz": "12 oy davomida"},
    "erd.inc_unstab": {"ru": "Нестабильность дохода", "uz": "Daromadning beqarorligi"},
    "erd.cv_desc_p1": {"ru": "вариации (CV). Показывает, скачет ли доход от {{ t('det.months') }}яца к {{ t('det.months') }}яцу.", "uz": "variatsiya (CV). Daromadning oydan oyga o'zgarishini ko'rsatadi."},
    "erd.cv_desc_p2": {"ru": "ы с нерегулярным доходом (CV > 1.0) получают умеренный штраф.", "uz": "lar (CV > 1.0 bo'lgan tartibsiz daromad bilan) o'rtacha jarima oladilar."},
    "erd.emp_desc": {"ru": "Госслужащие (\"byudjet\") и IT получают буст {{ t('pts') }}, безработные получают жесткий минус.", "uz": "Davlat xizmatchilari (\"byudjet\") va IT soha vakillari ballarga ega bo'lishadi, ishsizlar qattiq minus olishadi."},
    "erd.inc": {"ru": "Доход", "uz": "Daromad"}
}

with open("translations.py", "r", encoding="utf-8") as f:
    t_content = f.read()

extra_str = ""
for k, v in extra.items():
    extra_str += f'    "{k}": {v},\n'

t_content = t_content.replace('"pts": {"ru": "баллов", "uz": "ball"},', f'"pts": {{"ru": "баллов", "uz": "ball"}},\n{extra_str}')
with open("translations.py", "w", encoding="utf-8") as f:
    f.write(t_content)

replacements = {
    "Архитектура Данных (ERD)": "{{ t('erd.head_title') }}",
    " кредита\"": " {{ t('erd.loan_suffix') }}\"",
    "\"Срок\"": "\"{{ t('erd.term') }}\"",
    "Медианный доход": "{{ t('erd.median_inc') }}",
    "за 12 {{ t('det.months') }}яцев": "{{ t('erd.for_12_mo') }}",
    "Нестабильность дохода": "{{ t('erd.inc_unstab') }}",
    "вариации (CV). Показывает, скачет ли доход от {{ t('det.months') }}яца к {{ t('det.months') }}яцу.": "{{ t('erd.cv_desc_p1') }}",
    "ы с нерегулярным доходом (CV > 1.0) получают умеренный штраф.": "{{ t('erd.cv_desc_p2') }}",
    "Госслужащие (\"byudjet\") и IT получают буст {{ t('pts') }}, безработные получают жесткий минус.": "{{ t('erd.emp_desc') }}",
    "/Доход": "/{{ t('erd.inc') }}"
}

filepath = "templates/erd.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

for ru_text, jinja_tag in replacements.items():
    content = content.replace(ru_text, jinja_tag)
    
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
