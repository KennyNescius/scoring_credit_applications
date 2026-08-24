import os
import glob

rep = {
    '"Рассчитать решение"': '"{{ t(\'form.submit\') }}"',
    'Рассчитать решение</button>': '{{ t(\'form.submit\') }}</button>',
    '← Возврат в базу': '{{ t(\'btn.back\') }}',
    'What-If анализ': '{{ t(\'btn.whatif\') }}',
    'Заявка': '{{ t(\'det.title\') }}',
    
    # application_form.html fields
    'label for="yosh">Возраст</label>': 'label for="yosh">{{ t(\'f.age\') }}</label>',
    'label for="jins">Пол</label>': 'label for="jins">{{ t(\'f.gender\') }}</label>',
    '>Мужской<': '>{{ t("f.gender.m") }}<',
    '>Женский<': '>{{ t("f.gender.f") }}<',
    'label for="viloyat">Регион</label>': 'label for="viloyat">{{ t(\'f.region\') }}</label>',
    'label for="bandlik">Тип занятости</label>': 'label for="bandlik">{{ t(\'f.employment\') }}</label>',
    '>Частный сектор<': '>{{ t("f.employment.priv") }}<',
    '>Бюджет<': '>{{ t("f.employment.gov") }}<',
    '>IT-сфера<': '>{{ t("f.employment.it") }}<',
    '>Торговля<': '>{{ t("f.employment.trade") }}<',
    '>Строительство<': '>{{ t("f.employment.construct") }}<',
    '>Транспорт<': '>{{ t("f.employment.trans") }}<',
    '>Самозанятый<': '>{{ t("f.employment.self") }}<',
    '>Безработный<': '>{{ t("f.employment.unemp") }}<',
    'label for="talim">Образование</label>': 'label for="talim">{{ t(\'f.edu\') }}</label>',
    '>Высшее<': '>{{ t("f.edu.higher") }}<',
    '>Средне-специальное<': '>{{ t("f.edu.special") }}<',
    '>Среднее<': '>{{ t("f.edu.mid") }}<',
    'label for="ish_staji_oy">Стаж работы (месяцев)</label>': 'label for="ish_staji_oy">{{ t(\'f.exp\') }}</label>',
    'label for="deklaratsiya_daromad">Декларированный доход (UZS)</label>': 'label for="deklaratsiya_daromad">{{ t(\'f.income_decl\') }}</label>',
    'label for="oila_azolari">Членов семьи</label>': 'label for="oila_azolari">{{ t(\'f.family\') }}</label>',
    'label for="mijoz_boldi_oy">Срок клиентства (месяцев)</label>': 'label for="mijoz_boldi_oy">{{ t(\'f.client_len\') }}</label>',
    'label for="sorlgan_summa">Запрашиваемая сумма</label>': 'label for="sorlgan_summa">{{ t(\'f.amount\') }}</label>',
    'label for="maqsad">Цель</label>': 'label for="maqsad">{{ t(\'f.purpose\') }}</label>',
    '>Потребительский<': '>{{ t("f.purpose.consum") }}<',
    '>Автокредит<': '>{{ t("f.purpose.auto") }}<',
    '>Ипотека<': '>{{ t("f.purpose.mortgage") }}<',
    '>Кредитная карта<': '>{{ t("f.purpose.card") }}<',
    'label for="muddat_oy">Срок (месяцев)</label>': 'label for="muddat_oy">{{ t(\'f.term\') }}</label>',
    'label for="mavjud_oylik_yuk">Текущий платеж (заявка)</label>': 'label for="mavjud_oylik_yuk">{{ t(\'f.curr_pay\') }}</label>',

    # application_detail etc
    '<h3>Финальное решение</h3>': '<h3>{{ t(\'det.decision\') }}</h3>',
    '<h3>Сводка кредитоспособности</h3>': '<h3>{{ t(\'det.summary\') }}</h3>',
    '<th>Фактор</th>': '<th>{{ t("det.factor.name") }}</th>',
    '<th>Значение клиента</th>': '<th>{{ t("det.factor.val") }}</th>',
    '<th>Среднее по базе</th>': '<th>{{ t("det.factor.base") }}</th>',
    '<th>Баллы</th>': '<th>{{ t("det.factor.pts") }}</th>',
    '<h3>Причины отказа для клиента</h3>': '<h3>{{ t(\'det.reject_reasons\') }}</h3>',
    '>Подтвержденный расчетный доход<': '>{{ t("f.income_med") }}<',
    '>Нестабильность дохода (CV)<': '>{{ t("f.income_cv") }}<',
    '>Платеж по открытым кредитам<': '>{{ t("f.ext_pay") }}<',
    '>Остаток долга<': '>{{ t("f.ext_debt") }}<',
    '>Максимальная просрочка (дней)<': '>{{ t("f.max_delinq") }}<',
    '>Скоринговый балл:<': '>{{ t("det.score") }}:<',
    '>Вероятность дефолта:<': '>{{ t("det.pd") }}:<',
    '>Одобренный лимит:<': '>{{ t("det.limit") }}:<',
    '<h3>Основные факторы</h3>': '<h3>{{ t("det.factors") }}</h3>',
    
    # underwriter
    'Панель андеррайтера': '{{ t("uw.title") }}',
    'Оценка потока заявок': '{{ t("uw.desc") }}',
    '<th>ID Заявки</th>': '<th>{{ t("uw.table.id") }}</th>',
    '<th>Клиент</th>': '<th>{{ t("uw.table.client") }}</th>',
    '<th>Сумма</th>': '<th>{{ t("uw.table.amount") }}</th>',
    '<th>Балл (Score)</th>': '<th>{{ t("uw.table.score") }}</th>',
    '<th>Риск</th>': '<th>{{ t("uw.table.pd") }}</th>',
    '<th>Решение</th>': '<th>{{ t("uw.table.decision") }}</th>',
    '<th>Анализ</th>': '<th>{{ t("uw.table.view") }}</th>',
    '>Подробнее<': '>{{ t("index.cards.more") }}<',
    '>ОДОБРЕНО<': '>{{ t("status.approved") }}<',
    '>ОТКАЗАНО<': '>{{ t("status.rejected") }}<',
    
    # whatif
    '<h1>Симулятор отклонений</h1>': '<h1>{{ t("whatif.title") }}</h1>',
    '<p class="subtitle">Как изменение параметров повлияет на скоринговый балл?</p>': '<p class="subtitle">{{ t("whatif.desc") }}</p>',
    '>Симулировать<': '>{{ t("whatif.simulate") }}<',
    '<h3>Симулятор отклонений</h3>': '<h3>{{ t("whatif.title") }}</h3>',
    
    # model info
    '<h1>Информация о модели</h1>': '<h1>{{ t("model.info.title") }}</h1>',
    '<p class="subtitle">Whitebox параметры логистической регрессии и Scorecard-калибровки</p>': '<p class="subtitle">{{ t("model.info.desc") }}</p>',
    '<h3>Scorecard Параметры</h3>': '<h3>{{ t("model.params") }}</h3>',
    '>Ступень баллов (Factor)<': '>{{ t("model.factor") }}<',
    '>Смещение (Offset)<': '>{{ t("model.offset") }}<',
    '>Интерцепт (Intercept)<': '>{{ t("model.intercept") }}<',
    '<h3>Веса логистической регрессии (Log Odds)</h3>': '<h3>{{ t("model.coef.title") }}</h3>',
    '>Признак<': '>{{ t("model.table.feat") }}<',
    '>Коэффициент<': '>{{ t("model.table.coef") }}<',
    '>Значимость (IV)<': '>{{ t("model.table.iv") }}<',
    '>Влияние на риск<': '>{{ t("model.table.impact") }}<',
    '>Снижает дефолт<': '>{{ t("model.impact.pos") }}<',
    '>Повышает дефолт<': '>{{ t("model.impact.neg") }}<',
    
    # ERD
    '<h1>Схема данных (ERD)</h1>': '<h1>{{ t("erd.title") }}</h1>',
    '<p class="subtitle">Структура данных MVP: связи между Applicants, Applications, Flows и Loans</p>': '<p class="subtitle">{{ t("erd.subtitle") }}</p>',
    '<h3>Словарь сгенерированных признаков (Feature Engineering)</h3>': '<h3>{{ t("erd.dict.title") }}</h3>',
    'Эти показатели не лежат в сыром виде в базе, а вычисляются из связанных таблиц транзакций и кредитов. Именно они подаются в ML-модель после Target Encoding.': '{{ t("erd.dict.desc") }}',
    '<th>Фактор (Feature)</th>': '<th>{{ t("erd.col.fact") }}</th>',
    '<th>Источник / Формула</th>': '<th>{{ t("erd.col.form") }}</th>',
    '<th>Весомость в скоринге</th>': '<th>{{ t("erd.col.weight") }}</th>',
    '<th>Описание и влияние на модель</th>': '<th>{{ t("erd.col.desc") }}</th>',
}

for filename in glob.glob("/Users/Khurshid/hackathon/templates/*.html"):
    if filename.endswith("base.html") or filename.endswith("index.html"):
        continue
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    
    for k, v in rep.items():
        content = content.replace(k, v)
        
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

print("Translations applied!")
