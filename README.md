# Credit Scoring & Limit Engine

> CBU Coding Hackathon 2026 — Задача A2: Кредитный скоринг с объяснением решений

## Запуск

### Вариант 1: Docker (рекомендуется)
```bash
docker-compose up --build
```
Приложение доступно: http://localhost:5000

### Вариант 2: Make
```bash
make run
```

### Вариант 3: Вручную
```bash
pip install -r requirements.txt
python scoring_engine.py   # обучение + генерация результатов
python app.py              # запуск веб-приложения
```

## Структура проекта

| Файл | Назначение |
|------|-----------|
| `data_loader.py` | Загрузка CSV, объединение, feature engineering |
| `scoring_engine.py` | Модель, скоринг, объяснение решений, лимит |
| `db.py` | Persistence: immutable decision log + SCD Type 2 версионирование scorecard (SQLite) |
| `app.py` | Flask веб-приложение |
| `templates/` | HTML шаблоны (форма, андеррайтер, what-if) |
| `static/style.css` | Стили |
| `tests/test_scoring.py` | Автоматические тесты |
| `natija/kredit_qarorlari.csv` | Результат (генерируется автоматически) |
| `credit_scoring.db` | SQLite: `scorecard_versions` + `decisions` (генерируется автоматически при сборке) |

## Реализованные алгоритмы

1. **DTI/PTI расчёт** (обязательный) — Debt-to-Income и Payment-to-Income
2. **Cash-flow анализ** (обязательный) — медиана и CV дохода за 12 месяцев
3. **WOE/IV биннинг** (бонус) — Weight of Evidence и Information Value
4. **Логистическая регрессия** (бонус) — интерпретируемая модель
5. **Binary search лимита** (бонус) — поиск максимальной одобряемой суммы

## Base requirement: immutable decision log + SCD Type 2

`db.py` (SQLite, `credit_scoring.db`):

- **`decisions`** — append-only. При сборке образа заносится решение по всем 2700 заявкам датасета (`scoring_engine.py: seed_decision_log`); заявки через `/apply` логируются отдельно с `source="web_form"`. Хранятся языконезависимые данные (feature-ключ, points, direction) — человекочитаемый текст (`reason`, названия факторов) генерируется заново в языке текущей сессии на странице `/underwriter/<id>`, но сам факт решения (score/PD/decision) неизменен.
- **`scorecard_versions`** — SCD Type 2. Каждое обучение закрывает текущую активную версию (`valid_to = now`) и публикует новую (никогда не UPDATE на месте); каждая версия хранит свой pickle-файл модели (`models/model_<timestamp>.pkl`), так что старое решение всегда можно пересчитать той версией, которой оно было принято.

Подробности и схема — `ERD.md` / `DECISIONS.md`.

## Экраны

- `/` — Обзор (статистика, алгоритмы)
- `/apply` — Клиентская форма заявки
- `/underwriter` — Панель андеррайтера (все заявки)
- `/underwriter/<id>` — Детали заявки с разбивкой факторов
- `/whatif` — What-If симулятор
- `/model-info` — Информация о модели

## Тесты
```bash
python -m pytest tests/ -v
```

## Файл результатов

`natija/kredit_qarorlari.csv` — содержит все 540 тестовых заявок:

| Столбец | Описание |
|---------|----------|
| application_id | ID тестовой заявки |
| score | Скоринговый балл (0–1000) |
| pd | Вероятность дефолта |
| decision | toladi / defolt |
| sabab | Объяснение с факторами |
