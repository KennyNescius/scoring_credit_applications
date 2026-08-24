import os
import glob

extra = {
    "wi.title": {"ru": "What-If Симулятор", "uz": "What-If Simulyator"},
    "wi.subtitle": {"ru": "Измените параметры и посмотрите, как изменится решение", "uz": "Parametrlarni o'zgartiring va qaror qanday o'zgarishini ko'ring"},
    "wi.exp": {"ru": "Стаж (мес)", "uz": "Staj (oy)"},
    "wi.priv": {"ru": "Частный", "uz": "Xususiy"},
    "wi.spec": {"ru": "спец.", "uz": "maxsus"},
    "wi.finances": {"ru": "Финансы", "uz": "Moliya"},
    "wi.curr_pay": {"ru": "Текущие платежи (сум)", "uz": "Joriy to'lovlar (so'm)"},
    "wi.family": {"ru": "Семья", "uz": "Oila"},
    "wi.loans_cnt": {"ru": "Кол-во кредитов", "uz": "Kreditlar soni"},
    "wi.calc": {"ru": "Рассчитываем...", "uz": "Hisoblanmoqda..."},
    "wi.factor_val": {"ru": "(среднее:", "uz": "(o'rtacha:"},
    "model.subtitle": {"ru": "— параметры и коэффициенты", "uz": "— parametrlar va koeffitsientlar"},
    "model.params2": {"ru": "Параметры и Калибровка", "uz": "Parametrlar va Kalibrovka"},
    "model.f_count": {"ru": "Фичей в модели:", "uz": "Modeldagi xususiyatlar:"},
    "model.log_int": {"ru": "Логист. Интерсепт:", "uz": "Logistik Intersept:"},
    "model.calib": {"ru": "(Калибровка)", "uz": "(Kalibrovka)"},
    "model.base_score": {"ru": "Базовый скор (Base Score):", "uz": "Asosiy skor (Base Score):"},
    "model.base_odds": {"ru": "Базовые шансы (Base Odds):", "uz": "Asosiy imkoniyatlar (Base Odds):"},
    "model.pdo": {"ru": "для удвоения):", "uz": "ikki baravarga oshirish uchun):"},
    "model.factor": {"ru": "Множитель (Factor):", "uz": "Ko'paytiruvchi (Factor):"},
    "model.threshold": {"ru": "Критический Порог Одобрения:", "uz": "Kritik Ma'qullash Chegarasi:"},
    "model.all_coefs": {"ru": "Все коэффициенты", "uz": "Barcha koeffitsientlar"},
    "model.sorted_desc": {"ru": "Отсортированы по силе влияния. Средние значения используются как baseline.", "uz": "Ta'sir kuchiga qarab tartiblangan. O'rtacha qiymatlar baseline sifatida ishlatiladi."},
    "model.f_mean": {"ru": "Фича ({{ t('f.edu.mid') }} значение)", "uz": "Xususiyat ({{ t('f.edu.mid') }} qiymat)"},
    "model.impact_abs": {"ru": "Влияние (Abs)", "uz": "Ta'sir (Abs)"},
    "model.iv_desc": {"ru": "IV &lt; 0.02 — не предиктивен | 0.02–0.1 — слабый | 0.1–0.3 — средний | 0.3+ — сильный предиктор", "uz": "IV &lt; 0.02 — bashorat qilib bo'lmaydi | 0.02–0.1 — kuchsiz | 0.1–0.3 — o'rtacha | 0.3+ — kuchli bashoratchi"},
    "model.algos": {"ru": "Реализованные алгоритмы", "uz": "Amalga oshirilgan algoritmlar"},
    "model.algo1": {"ru": "DTI/PTI (обязательный)", "uz": "DTI/PTI (majburiy)"},
    "model.algo1_desc1": {"ru": "текущие платежи + платежи по существующим кредитам) / медианный доход", "uz": "joriy to'lovlar + mavjud kreditlar bo'yicha to'lovlar) / median daromad"},
    "model.algo1_desc2": {"ru": "все платежи + платёж по новому кредиту) / медианный доход", "uz": "barcha to'lovlar + yangi kredit bo'yicha to'lov) / median daromad"},
    "model.algo1_desc3": {"ru": "Big-O: O(n) — линейный проход по кредитам", "uz": "Big-O: O(n) — kreditlar bo'ylab chiziqli o'tish"},
    "model.algo2": {"ru": "Cash-flow анализ (обязательный)", "uz": "Cash-flow tahlili (majburiy)"},
    "model.algo2_desc1": {"ru": "Медиана и вариабельность дохода за 12 {{ t('det.months') }}яцев", "uz": "12 {{ t('det.months') }} davomida daromadning medianasi va o'zgaruvchanligi"},
    "model.algo2_desc3": {"ru": "Big-O: O(m) — линейный проход по {{ t('det.months') }}яцам", "uz": "Big-O: O(m) — {{ t('det.months') }} bo'ylab chiziqli o'tish"},
    "model.algo3_desc1": {"ru": "Квантильный биннинг (5 бинов), Weight of Evidence, Information Value", "uz": "Kvantil binning (5 ta bin), Weight of Evidence, Information Value"},
    "model.algo3_desc2": {"ru": "IV используется для оценки предиктивной силы фичей", "uz": "IV xususiyatlarning bashorat qilish kuchini baholash uchun ishlatiladi"},
    "model.algo4_desc1": {"ru": "sklearn LogisticRegression с class_weight='balanced'", "uz": "sklearn LogisticRegression class_weight='balanced' bilan"},
    "model.algo4_desc2": {"ru": "ы интерпретируемы → вклад факторов в баллах", "uz": "lar izohlanadi → omillarning ballardagi hissasi"},
    "model.algo5_desc1": {"ru": "Поиск максимальной {{ t('det.sum') }}мы, при которой заявка ещё одобряется", "uz": "Ariza hali ham ma'qullanadigan maksimal {{ t('det.sum') }}mani izlash"},
    "model.algo5_desc3": {"ru": "Big-O: O(30 × model_predict) — 30 итераций бинарного поиска", "uz": "Big-O: O(30 × model_predict) — binar qidiruvning 30 ta iteratsiyasi"}
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
    "What-If Симулятор": "{{ t('wi.title') }}",
    "Измените параметры и посмотрите, как изменится решение": "{{ t('wi.subtitle') }}",
    "Стаж (мес)": "{{ t('wi.exp') }}",
    "Частный": "{{ t('wi.priv') }}",
    " спец.": " {{ t('wi.spec') }}",
    "Финансы": "{{ t('wi.finances') }}",
    "Текущие платежи (сум)": "{{ t('wi.curr_pay') }}",
    "Семья": "{{ t('wi.family') }}",
    "Кол-во кредитов": "{{ t('wi.loans_cnt') }}",
    "Рассчитываем...": "{{ t('wi.calc') }}",
    "(среднее:": "{{ t('wi.factor_val') }}",
    "— параметры и коэффициенты": "{{ t('model.subtitle') }}",
    "Параметры и Калибровка": "{{ t('model.params2') }}",
    "Фичей в модели:": "{{ t('model.f_count') }}",
    "Логист. Интерсепт:": "{{ t('model.log_int') }}",
    "(Калибровка)": "{{ t('model.calib') }}",
    "Базовый скор (Base Score):": "{{ t('model.base_score') }}",
    "Базовые шансы (Base Odds):": "{{ t('model.base_odds') }}",
    "для удвоения):": "{{ t('model.pdo') }}",
    "Множитель (Factor):": "{{ t('model.factor') }}",
    "Критический Порог Одобрения:": "{{ t('model.threshold') }}",
    "Все коэффициенты": "{{ t('model.all_coefs') }}",
    "Отсортированы по силе влияния. Средние значения используются как baseline.": "{{ t('model.sorted_desc') }}",
    "Фича ({{ t('f.edu.mid') }} значение)": "{{ t('model.f_mean') }}",
    "Влияние (Abs)": "{{ t('model.impact_abs') }}",
    "IV &lt; 0.02 — не предиктивен | 0.02–0.1 — слабый | 0.1–0.3 — средний | 0.3+ — сильный предиктор": "{{ t('model.iv_desc') }}",
    "Реализованные алгоритмы": "{{ t('model.algos') }}",
    "DTI/PTI (обязательный)": "{{ t('model.algo1') }}",
    "текущие платежи + платежи по существующим кредитам) / медианный доход": "{{ t('model.algo1_desc1') }}",
    "все платежи + платёж по новому кредиту) / медианный доход": "{{ t('model.algo1_desc2') }}",
    "Big-O: O(n) — линейный проход по кредитам": "{{ t('model.algo1_desc3') }}",
    "Cash-flow анализ (обязательный)": "{{ t('model.algo2') }}",
    "Медиана и вариабельность дохода за 12 {{ t('det.months') }}яцев": "{{ t('model.algo2_desc1') }}",
    "Big-O: O(m) — линейный проход по {{ t('det.months') }}яцам": "{{ t('model.algo2_desc3') }}",
    "Квантильный биннинг (5 бинов), Weight of Evidence, Information Value": "{{ t('model.algo3_desc1') }}",
    "IV используется для оценки предиктивной силы фичей": "{{ t('model.algo3_desc2') }}",
    "sklearn LogisticRegression с class_weight='balanced'": "{{ t('model.algo4_desc1') }}",
    "ы интерпретируемы → вклад факторов в баллах": "{{ t('model.algo4_desc2') }}",
    "Поиск максимальной {{ t('det.sum') }}мы, при которой заявка ещё одобряется": "{{ t('model.algo5_desc1') }}",
    "Big-O: O(30 × model_predict) — 30 итераций бинарного поиска": "{{ t('model.algo5_desc3') }}"
}

for filepath in ["templates/whatif.html", "templates/model_info.html"]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    for ru_text, jinja_tag in sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True):
        content = content.replace(ru_text, jinja_tag)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
