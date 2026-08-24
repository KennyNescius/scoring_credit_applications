# Схема данных (ERD) — CBU Coding Hackathon 2026

Данная схема описывает структуру данных, используемых в модуле скоринга на этапе MVP (считывание из CSV файлов). В будущем эти сущности мигрируют в реляционную PostgreSQL базу.

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

    APPLICANTS ||--o{ APPLICATIONS : "submits"
    APPLICANTS ||--o{ EXISTING_LOANS : "has"
    APPLICANTS ||--o{ MONTHLY_FLOWS : "generates"
```

## Пояснения к модели
- **APPLICANTS** — базовая таблица профилей клиентов.
- **APPLICATIONS** — таблица заявок, содержащая параметры запроса и целевую переменную `natija` (Target), которая отсутствует в скрытом тестовом датасете 2-го дня.
- **EXISTING_LOANS** — кредитная история клиента (Кредитный регистр), где аккумулируются открытые займы. Из них мы высчитываем долговую нагрузку и дисциплину платежей.
- **MONTHLY_FLOWS** — выписки по счету клиента за последние 12 месяцев. Используется для расчета стабильности (Coefficient of Variance) и реального медианного дохода.
