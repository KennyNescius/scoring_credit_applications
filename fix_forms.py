import os

extra = {
    "form.on_loan": {"ru": "на кредит", "uz": "kreditga"}
}

with open("translations.py", "r", encoding="utf-8") as f:
    t_content = f.read()

extra_str = ""
for k, v in extra.items():
    extra_str += f'    "{k}": {v},\n'

t_content = t_content.replace('"pts": {"ru": "баллов", "uz": "ball"},', f'"pts": {{"ru": "баллов", "uz": "ball"}},\n{extra_str}')
with open("translations.py", "w", encoding="utf-8") as f:
    f.write(t_content)

replacements_form = {
    "Подача заявки": "{{ t('nav.apply') }}",
    " на кредит": " {{ t('form.on_loan') }}",
    " кредита (сум)": " {{ t('wi.amount_lbl') }}",
    " кредита": " {{ t('erd.loan_suffix') }}",
    "{{ t('f.gender') }}учить решение": "{{ t('form.submit3') }}",
    "(среднее:": "{{ t('wi.factor_val') }}"
}

filepath = "templates/application_form.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

for ru_text, jinja_tag in replacements_form.items():
    content = content.replace(ru_text, jinja_tag)
    
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
