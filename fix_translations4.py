import os
import glob

extra = {
    "wi.amount_lbl": {"ru": "кредита (сум)", "uz": "kredit (so'm)"},
    "wi.days_lbl": {"ru": "(дн)", "uz": "(kun)"},
    "wi.factors_pl": {"ru": "ы", "uz": "lar"},
    "model.bonus": {"ru": "(бонус)", "uz": "(bonus)"}
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
    "кредита (сум)": "{{ t('wi.amount_lbl') }}",
    "(дн)": "{{ t('wi.days_lbl') }}",
    "{{ t('det.factor.name') }}ы": "{{ t('det.factor.name') }}{{ t('wi.factors_pl') }}",
    "(бонус)": "{{ t('model.bonus') }}"
}

for filepath in ["templates/whatif.html", "templates/model_info.html"]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    for ru_text, jinja_tag in replacements.items():
        content = content.replace(ru_text, jinja_tag)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
