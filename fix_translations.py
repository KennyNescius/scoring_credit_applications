import os
import glob

# Extra keys to add to translations.py
extra_translations = {
    "btn.back": {"ru": "← Назад", "uz": "← Orqaga"},
    "det.max_limit": {"ru": "Макс. лимит:", "uz": "Maks. limit:"},
    "det.actual": {"ru": "Факт:", "uz": "Fakt:"},
    "det.unknown": {"ru": "Неизвестно", "uz": "Noma'lum"},
    "det.applicant": {"ru": "Заявитель", "uz": "Ariza beruvchi"},
    "det.name": {"ru": "Имя:", "uz": "Ism:"},
    "det.loan": {"ru": "Кредит", "uz": "Kredit"},
    "det.loans_count": {"ru": "Кредитов:", "uz": "Kreditlar:"},
    "det.factors_breakdown": {"ru": "Разбивка по факторам", "uz": "Omillar bo'yicha taqsimot"},
    "det.val": {"ru": "Значение:", "uz": "Qiymat:"},
    "det.log": {"ru": "Журнал решения (immutable)", "uz": "Qaror jurnali (immutable)"},
    "form.desc": {"ru": "Заполните данные для получения кредитного решения", "uz": "Kredit qarorini olish uchun ma'lumotlarni to'ldiring"},
    "form.app_data": {"ru": "Данные заявителя", "uz": "Ariza beruvchi ma'lumotlari"},
    "form.loan_params": {"ru": "Параметры кредита", "uz": "Kredit parametrlari"},
    "form.high_risk": {"ru": "Высокий риск", "uz": "Yuqori xavf"},
    "form.low_risk": {"ru": "Низкий риск", "uz": "Past xavf"},
    "uw.approved": {"ru": "Одобренные", "uz": "Ma'qullangan"},
    "uw.rejected": {"ru": "Отклоненные", "uz": "Rad etilgan"},
    "uw.all_apps": {"ru": "Все заявки", "uz": "Barcha arizalar"},
    "uw.train": {"ru": "Train (исторические)", "uz": "Train (tarixiy)"},
    "uw.test": {"ru": "Test (новые)", "uz": "Test (yangi)"},
    "uw.filter": {"ru": "Фильтр:", "uz": "Filtr:"},
    "uw.decision": {"ru": "Решение:", "uz": "Qaror:"},
    "uw.apply": {"ru": "Применить", "uz": "Qo'llash"},
    "form.submit2": {"ru": "получить решение", "uz": "qarorni olish"},
    "pts2": {"ru": "б.", "uz": "b."}
}

# 1. Update translations.py
with open("translations.py", "r", encoding="utf-8") as f:
    t_content = f.read()

# Insert the new dict keys into TRANSLATIONS before "feat.yosh"
extra_str = ""
for k, v in extra_translations.items():
    extra_str += f'    "{k}": {v},\n'

t_content = t_content.replace('"pts": {"ru": "баллов", "uz": "ball"},', f'"pts": {{"ru": "баллов", "uz": "ball"}},\n{extra_str}')
with open("translations.py", "w", encoding="utf-8") as f:
    f.write(t_content)

# 2. String replacements in HTML
replacements = {
    "← Назад": "{{ t('btn.back') }}",
    "баллов": "{{ t('pts') }}",
    "Порог:": "{{ t('index.cards.threshold') }}",
    "Макс. лимит:": "{{ t('det.max_limit') }}",
    "Факт:": "{{ t('det.actual') }}",
    "Неизвестно": "{{ t('det.unknown') }}",
    "Версия модели:": "{{ t('index.cards.version') }}",
    "Данные заявителя": "{{ t('form.app_data') }}",
    "Заявитель": "{{ t('det.applicant') }}",
    "Имя:": "{{ t('det.name') }}",
    "Занятость:": "{{ t('f.employment') }}",
    "Стаж:": "{{ t('f.exp') }}",
    "Доход:": "{{ t('f.income_decl') }}",
    "Семья:": "{{ t('f.family') }}",
    "Кредит": "{{ t('det.loan') }}",
    "Медианный доход:": "{{ t('f.income_med') }}",
    "CV дохода:": "{{ t('f.income_cv') }}",
    "Макс. просрочка:": "{{ t('f.max_delinq') }}",
    "Кредитов:": "{{ t('det.loans_count') }}",
    "Разбивка по факторам": "{{ t('det.factors_breakdown') }}",
    "Значение:": "{{ t('det.val') }}",
    "Журнал решения (immutable)": "{{ t('det.log') }}",
    "Заполните данные для получения кредитного решения": "{{ t('form.desc') }}",
    "Доход (сум/мес)": "{{ t('f.income_decl') }}",
    "Параметры кредита": "{{ t('form.loan_params') }}",
    "Срок (мес)": "{{ t('f.term') }}",
    "Текущие платежи (сум/мес)": "{{ t('f.curr_pay') }}",
    "получить решение": "{{ t('form.submit2') }}",
    "Высокий риск": "{{ t('form.high_risk') }}",
    "Низкий риск": "{{ t('form.low_risk') }}",
    "Одобренные": "{{ t('uw.approved') }}",
    "Отклоненные": "{{ t('uw.rejected') }}",
    "Все заявки": "{{ t('uw.all_apps') }}",
    "Train (исторические)": "{{ t('uw.train') }}",
    "Test (новые)": "{{ t('uw.test') }}",
    "Фильтр:": "{{ t('uw.filter') }}",
    "Решение:": "{{ t('uw.decision') }}",
    "Применить": "{{ t('uw.apply') }}",
    "Своё дело": "{{ t('f.employment.self') }}",
    "специальное": "{{ t('f.edu.special') }}",
    "Стаж работы (мес)": "{{ t('f.exp') }}",
    "б.": "{{ t('pts2') }}"
}

for filepath in glob.glob("templates/*.html"):
    if filepath.endswith("base.html"): continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Sort by length descending to replace longest strings first
    for ru_text, jinja_tag in sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True):
        content = content.replace(ru_text, jinja_tag)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
