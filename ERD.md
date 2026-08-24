# Схема данных (ERD) — CBU Coding Hackathon 2026

Источник данных (CSV) и слой персистентности (SQLite, `db.py`) — два разных набора таблиц:

- **APPLICANTS / APPLICATIONS / EXISTING_LOANS / MONTHLY_FLOWS** — считываются из предоставленных CSV (`data_loader.py`), только на чтение.
- **SCORECARD_VERSIONS / DECISIONS** — реально персистентны в `credit_scoring.db` (SQLite), пишутся приложением. Это и есть immutable decision log + SCD Type 2 версионирование scorecard из базового требования ТЗ.
- **SETTINGS** — key/value, рантайм-конфигурация (не из ТЗ) — сейчас единственное применение: включение/значение affordability-потолка для `find_max_limit()`, редактируется на `/model-info`.

```mermaid
erDiagram
    APPLICANTS {
        string applicant_id PK
        string ism "Имя клиента"
        int yosh "Возраст"
        string jins "Пол"
        string viloyat "Регион"
        string bandlik "Занятость"
        string talim "Образование"
        int ish_staji_oy "Стаж работы"
        int deklaratsiya_daromad "Декл. доход"
        int oila_azolari "Членов семьи"
        int mijoz_boldi_oy "Срок клиентства"
    }

    APPLICATIONS {
        string application_id PK
        string applicant_id FK
        int sorlgan_summa "Запрошенная сумма"
        string maqsad "Цель кредита"
        int muddat_oy "Срок"
        int mavjud_oylik_yuk "Текущий платеж"
        string natija "Таргет (toladi/defolt)"
    }

    EXISTING_LOANS {
        string loan_id PK
        string applicant_id FK
        int qoldiq "Остаток суммы"
        int oylik_tolov "Ежемесячный платеж"
        int max_kechikish_kun "Макс. просрочка"
    }

    MONTHLY_FLOWS {
        string applicant_id FK "Composite Key"
        string oy FK "Месяц транзакции"
        int kirim "Входящий поток"
        int chiqim "Исходящий поток"
        int naqd_yechish "Снятие наличных"
        int oy_oxiri_qoldiq "Остаток на конец мес."
    }

    SCORECARD_VERSIONS {
        int version_id PK
        string created_at
        string valid_from
        string valid_to "NULL = активная версия"
        string model_path "уникальный pickle для этой версии"
        float train_auc
        float test_auc
        float test_gini
        int n_train
        string description
    }

    DECISIONS {
        int decision_id PK
        string created_at
        string application_id FK "ссылается на APPLICATIONS.application_id, либо WEB-...  для ручных заявок"
        string applicant_id
        int scorecard_version_id FK
        int score
        float pd
        string decision "toladi / defolt"
        int threshold
        string source "dataset / web_form"
        string factors_json "языконезависимые factor-баллы, заморожены"
        string input_snapshot_json "заморожены сырые фичи на момент решения"
    }

    SETTINGS {
        string key PK
        string value "напр. affordability_cap_enabled, affordability_cap_pti"
    }

    APPLICANTS ||--o{ APPLICATIONS : "submits"
    APPLICANTS ||--o{ EXISTING_LOANS : "has"
    APPLICANTS ||--o{ MONTHLY_FLOWS : "generates"
    APPLICATIONS ||--o{ DECISIONS : "resolved by"
    SCORECARD_VERSIONS ||--o{ DECISIONS : "scored with"
```

## Пояснения к модели
- **APPLICANTS** — базовая таблица профилей клиентов.
- **APPLICATIONS** — таблица заявок, содержащая параметры запроса и целевую переменную `natija` (Target), которая отсутствует в скрытом тестовом датасете 2-го дня.
- **EXISTING_LOANS** — кредитная история клиента (Кредитный регистр), где аккумулируются открытые займы. Из них мы высчитываем долговую нагрузку и дисциплину платежей.
- **MONTHLY_FLOWS** — выписки по счету клиента за последние 12 месяцев. Используется для расчета стабильности (Coefficient of Variance) и реального медианного дохода.
- **SCORECARD_VERSIONS** — SCD Type 2. При каждом обучении (`scoring_engine.py: train_publish_and_seed`) закрывается текущая активная версия (`valid_to = now`) и вставляется новая — никогда не UPDATE на месте.
- **DECISIONS** — append-only immutable log. При сборке образа заносится решение по каждой из 2700 заявок датасета; заявки через `/apply` логируются отдельно (`source="web_form"`). Хранится замороженный языконезависимый снимок (feature-ключи, баллы, направление), человекочитаемый текст (`reason`, названия факторов) генерируется заново в языке текущей сессии при просмотре — сам факт решения от языка интерфейса не зависит.
- **SETTINGS** — не связана FK ни с чем, простое key/value-хранилище рантайм-настроек. Единственное текущее применение — affordability-потолок PTI для `find_max_limit()` (см. DECISIONS.md, п.5): выключен по умолчанию, включается и настраивается формой на `/model-info` без пересборки образа.
