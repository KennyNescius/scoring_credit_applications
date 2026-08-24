import os
import glob
import re

extra_translations = {
    # Application Form
    "form.income": {"ru": "Доход (сум/мес)", "uz": "Daromad (so'm/oy)"},
    "form.loan_amount": {"ru": "Сумма кредита (сум)", "uz": "Kredit summasi (so'm)"},
    "form.curr_pay": {"ru": "Текущие платежи (сум/мес)", "uz": "Joriy to'lovlar (so'm/oy)"},
    "form.client_months": {"ru": "Стаж клиента банка (мес)", "uz": "Bank mijozi staji (oy)"},
    "form.error": {"ru": "Ошибка", "uz": "Xatolik"},
    "form.fill_err": {"ru": "Пожалуйста, заполните все числовые поля корректно.", "uz": "Iltimos, barcha raqamli maydonlarni to'g'ri to'ldiring."},
    "form.submit3": {"ru": "Получить решение", "uz": "Qarorni olish"},
    
    # Application Detail
    "det.pd_label": {"ru": "PD (вер-ть дефолта):", "uz": "PD (defolt ehtimoli):"},
    "det.app_info": {"ru": "Данные заявителя", "uz": "Ariza beruvchi ma'lumotlari"},
    "det.loan_info": {"ru": "Данные кредита", "uz": "Kredit ma'lumotlari"},
    "det.median_inc": {"ru": "Медианный доход:", "uz": "Median daromad:"},
    "det.cv_inc": {"ru": "CV дохода:", "uz": "Daromad CV:"},
    "det.max_del": {"ru": "Макс. просрочка:", "uz": "Maks. kechikish:"},
    "det.loans_cnt": {"ru": "Кредитов:", "uz": "Kreditlar soni:"},
    "det.term": {"ru": "Срок:", "uz": "Muddat:"},
    "det.employment": {"ru": "Занятость", "uz": "Bandlik"},
    "det.staj": {"ru": "Стаж", "uz": "Staj"},
    "det.income": {"ru": "Доход", "uz": "Daromad"},
    "det.family": {"ru": "Семья", "uz": "Oila"},
    "det.days": {"ru": "дн", "uz": "kun"},
    "det.months": {"ru": "мес", "uz": "oy"},
    "det.sum": {"ru": "сум", "uz": "so'm"},
    "det.people": {"ru": "чел", "uz": "kishi"},
    "det.years": {"ru": "лет", "uz": "yosh"},
    
    # ERD
    "erd.title2": {"ru": "Архитектура и Словарь Данных", "uz": "Arxitektura va Ma'lumotlar Lug'ati"},
    "erd.desc2": {"ru": "Интерактивная схема таблиц (ERD) и описание вычислимых факторов (Feature Engineering)", "uz": "Interaktiv jadvallar sxemasi (ERD) va hisoblanuvchi omillar tavsifi (Feature Engineering)"},
    "erd.btn.zoom_in": {"ru": "Увеличить", "uz": "Kattalashtirish"},
    "erd.btn.zoom_out": {"ru": "Уменьшить", "uz": "Kichraytirish"},
    "erd.btn.reset": {"ru": "Сбросить", "uz": "Tiklash"},
    
    "erd.f1": {"ru": "Имя клиента", "uz": "Mijoz ismi"},
    "erd.f2": {"ru": "Занятость", "uz": "Bandlik"},
    "erd.f3": {"ru": "Стаж работы", "uz": "Ish staji"},
    "erd.f4": {"ru": "Декл. доход", "uz": "Dekl. daromad"},
    "erd.f5": {"ru": "Срок клиентства", "uz": "Mijozlik muddati"},
    "erd.f6": {"ru": "Запрошенная сумма", "uz": "So'ralgan summa"},
    "erd.f7": {"ru": "Текущий платеж", "uz": "Joriy to'lov"},
    "erd.f8": {"ru": "Таргет (toladi/defolt)", "uz": "Target (toladi/defolt)"},
    "erd.f9": {"ru": "Остаток суммы", "uz": "Summa qoldig'i"},
    "erd.f10": {"ru": "Ежемесячный платеж", "uz": "Oylik to'lov"},
    "erd.f11": {"ru": "Макс. просрочка", "uz": "Maks. kechikish"},
    "erd.f12": {"ru": "Месяц транзакции", "uz": "Tranzaksiya oyi"},
    "erd.f13": {"ru": "Входящий поток", "uz": "Kiruvchi oqim"},
    "erd.f14": {"ru": "Исходящий поток", "uz": "Chiquvchi oqim"},
    "erd.f15": {"ru": "Снятие наличных", "uz": "Naqd pul yechish"},
    "erd.f16": {"ru": "Остаток на конец мес.", "uz": "Oy oxiridagi qoldiq"},
    
    "erd.lvl.crit": {"ru": "Критическая", "uz": "Kritik"},
    "erd.lvl.high": {"ru": "Высокая", "uz": "Yuqori"},
    "erd.lvl.mid": {"ru": "Средняя", "uz": "O'rta"},
    "erd.lbl.rel1": {"ru": "Отношение всех ежемесячных платежей (вкл. новый кредит) к подтвержденному доходу.", "uz": "Barcha oylik to'lovlarning (yangi kreditni qo'shganda) tasdiqlangan daromadga nisbati."},
    "erd.lbl.infl": {"ru": "Влияние:", "uz": "Ta'siri:"},
    "erd.lbl.rel2": {"ru": "Превышение порога в 50% вызывает моментальное обрушение скорингового балла и отказ.", "uz": "50% chegarasidan oshib ketish skoring ballining keskin tushishiga va rad etilishiga olib keladi."},
    "erd.lbl.rel3": {"ru": "Отношение только текущей (уже существующей) долговой нагрузки к доходу.", "uz": "Faqat joriy qarz yukining daromadga nisbati."},
    "erd.lbl.rel4": {"ru": "Сильно штрафует закредитованных клиентов еще до учета новой суммы.", "uz": "Yangi summani hisobga olishdan oldin ham qarzga botgan mijozlarni qattiq jarimalaydi."},
    
    "erd.lbl.med1": {"ru": "Мы игнорируем сырое поле", "uz": "Biz xom maydonni e'tiborsiz qoldiramiz"},
    "erd.lbl.med2": {"ru": "и парсим реальные остатки по транзакциям.", "uz": "va tranzaksiyalar bo'yicha haqiqiy qoldiqlarni tahlil qilamiz."},
    "erd.lbl.med3": {"ru": "Базовый знаменатель для всех финансовых проверок. Обрабатывается Winsorization (обрезка 1-99 перцентилей от выбросов).", "uz": "Barcha moliyaviy tekshiruvlar uchun asosiy maxraj. Winsorization (chiqindilarni 1-99 foizini kesish) orqali qayta ishlanadi."},
    
    "erd.lbl.cv1": {"ru": "Коэффициент вариации (CV). Показывает, скачет ли доход от месяца к месяцу.", "uz": "Variatsiya koeffitsienti (CV). Daromad oydan oyga o'zgarishini ko'rsatadi."},
    "erd.lbl.cv2": {"ru": "Клиенты с нерегулярным доходом (CV > 1.0) получают умеренный штраф.", "uz": "Muntazam bo'lmagan daromadga ega (CV > 1.0) mijozlar o'rtacha jarimaga tortiladi."},
    
    "erd.lbl.emp1": {"ru": "Вместо ручного кодирования модель считает исторический % невозвратов для каждой должности.", "uz": "Qo'lda kodlash o'rniga model har bir lavozim uchun tarixiy qaytarmaslik % ni hisoblaydi."},
    "erd.lbl.emp2": {"ru": "Госслужащие (\"byudjet\") и IT получают буст баллов, безработные получают жесткий минус.", "uz": "Davlat xizmatchilari (\"byudjet\") va IT soha vakillari ballar oshishini oladi, ishsizlar esa qattiq minus oladi."},
    
    "erd.lbl.del1": {"ru": "Качество обслуживания прошлых ссуд.", "uz": "O'tgan kreditlarga xizmat ko'rsatish sifati."},
    "erd.lbl.del2": {"ru": "Единственная просрочка > 30 дней в кредитной истории сильно бьет по баллам.", "uz": "Kredit tarixidagi > 30 kunlik yagona kechikish ballarga qattiq zarba beradi."},
    
    "erd.lbl.lti1": {"ru": "Мультипликатор кредита относительно месячной зарплаты (Loan-to-Income / LTI).", "uz": "Oylik ish haqiga nisbatan kredit multiplikatori (Loan-to-Income / LTI)."},
    "erd.lbl.lti2": {"ru": "Запрашивать >15 окладов рискованно, влечет понижение скора.", "uz": ">15 ta oylik maosh so'rash xavfli, skor pasayishiga olib keladi."},
    
    # Model info
    "model.info.base": {"ru": "Базовый риск", "uz": "Asosiy xavf"},
    "model.info.const": {"ru": "Константа логистической регрессии", "uz": "Logistik regressiya konstantasi"}
}

with open("translations.py", "r", encoding="utf-8") as f:
    t_content = f.read()

extra_str = ""
for k, v in extra_translations.items():
    extra_str += f'    "{k}": {v},\n'

t_content = t_content.replace('"pts": {"ru": "баллов", "uz": "ball"},', f'"pts": {{"ru": "баллов", "uz": "ball"}},\n{extra_str}')
with open("translations.py", "w", encoding="utf-8") as f:
    f.write(t_content)

replacements = {
    "Доход (сум/мес)": "{{ t('form.income') }}",
    "Сумма кредита (сум)": "{{ t('form.loan_amount') }}",
    "Текущие платежи (сум/мес)": "{{ t('form.curr_pay') }}",
    "банка (мес)": "{{ t('form.client_months') }}",
    "Ошибка": "{{ t('form.error') }}",
    "Пожалуйста, заполните все числовые поля корректно.": "{{ t('form.fill_err') }}",
    "получить решение": "{{ t('form.submit3') }}",
    "PD (вер-ть дефолта):": "{{ t('det.pd_label') }}",
    "Медианный доход:": "{{ t('det.median_inc') }}",
    "CV дохода:": "{{ t('det.cv_inc') }}",
    "Макс. просрочка:": "{{ t('det.max_del') }}",
    "Кредитов:": "{{ t('det.loans_cnt') }}",
    "Срок:": "{{ t('det.term') }}",
    "Занятость:": "{{ t('det.employment') }}:",
    "Стаж:": "{{ t('det.staj') }}:",
    "Доход:": "{{ t('det.income') }}:",
    "Семья:": "{{ t('det.family') }}:",
    " дн": " {{ t('det.days') }}",
    " мес": " {{ t('det.months') }}",
    " сум": " {{ t('det.sum') }}",
    " чел": " {{ t('det.people') }}",
    " лет": " {{ t('det.years') }}",
    "Архитектура и Словарь Данных": "{{ t('erd.title2') }}",
    "Интерактивная схема таблиц (ERD) и описание вычислимых факторов (Feature Engineering)": "{{ t('erd.desc2') }}",
    "Увеличить": "{{ t('erd.btn.zoom_in') }}",
    "Уменьшить": "{{ t('erd.btn.zoom_out') }}",
    "Сбросить": "{{ t('erd.btn.reset') }}",
    "Имя клиента": "{{ t('erd.f1') }}",
    "Занятость": "{{ t('erd.f2') }}",
    "Стаж работы": "{{ t('erd.f3') }}",
    "Декл. доход": "{{ t('erd.f4') }}",
    "Срок клиентства": "{{ t('erd.f5') }}",
    "Запрошенная сумма": "{{ t('erd.f6') }}",
    "Текущий платеж": "{{ t('erd.f7') }}",
    "Таргет (toladi/defolt)": "{{ t('erd.f8') }}",
    "Остаток суммы": "{{ t('erd.f9') }}",
    "Ежемесячный платеж": "{{ t('erd.f10') }}",
    "Макс. просрочка": "{{ t('erd.f11') }}",
    "Месяц транзакции": "{{ t('erd.f12') }}",
    "Входящий поток": "{{ t('erd.f13') }}",
    "Исходящий поток": "{{ t('erd.f14') }}",
    "Снятие наличных": "{{ t('erd.f15') }}",
    "Остаток на конец мес.": "{{ t('erd.f16') }}",
    "Критическая": "{{ t('erd.lvl.crit') }}",
    "Высокая": "{{ t('erd.lvl.high') }}",
    "Средняя": "{{ t('erd.lvl.mid') }}",
    "Отношение всех ежемесячных платежей (вкл. новый кредит) к подтвержденному доходу.": "{{ t('erd.lbl.rel1') }}",
    "Влияние:": "{{ t('erd.lbl.infl') }}",
    "Превышение порога в 50% вызывает моментальное обрушение скорингового балла и отказ.": "{{ t('erd.lbl.rel2') }}",
    "Отношение только текущей (уже существующей) долговой нагрузки к доходу.": "{{ t('erd.lbl.rel3') }}",
    "Сильно штрафует закредитованных клиентов еще до учета новой суммы.": "{{ t('erd.lbl.rel4') }}",
    "Мы игнорируем сырое поле": "{{ t('erd.lbl.med1') }}",
    "и парсим реальные остатки по транзакциям.": "{{ t('erd.lbl.med2') }}",
    "Базовый знаменатель для всех финансовых проверок. Обрабатывается Winsorization (обрезка 1-99 перцентилей от выбросов).": "{{ t('erd.lbl.med3') }}",
    "Коэффициент вариации (CV). Показывает, скачет ли доход от месяца к месяцу.": "{{ t('erd.lbl.cv1') }}",
    "Клиенты с нерегулярным доходом (CV > 1.0) получают умеренный штраф.": "{{ t('erd.lbl.cv2') }}",
    "Вместо ручного кодирования модель считает исторический % невозвратов для каждой должности.": "{{ t('erd.lbl.emp1') }}",
    "Госслужащие (\"byudjet\") и IT получают буст баллов, безработные получают жесткий минус.": "{{ t('erd.lbl.emp2') }}",
    "Качество обслуживания прошлых ссуд.": "{{ t('erd.lbl.del1') }}",
    "Единственная просрочка > 30 дней в кредитной истории сильно бьет по баллам.": "{{ t('erd.lbl.del2') }}",
    "Мультипликатор кредита относительно месячной зарплаты (Loan-to-Income / LTI).": "{{ t('erd.lbl.lti1') }}",
    "Запрашивадить >15 окладов рискованно, влечет понижение скора.": "{{ t('erd.lbl.lti2') }}",
    "Запрашивать >15 окладов рискованно, влечет понижение скора.": "{{ t('erd.lbl.lti2') }}",
    "Базовый риск": "{{ t('model.info.base') }}",
    "Константа логистической регрессии": "{{ t('model.info.const') }}"
}

for filepath in glob.glob("templates/*.html"):
    if filepath.endswith("base.html"): continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    for ru_text, jinja_tag in sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True):
        content = content.replace(ru_text, jinja_tag)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
