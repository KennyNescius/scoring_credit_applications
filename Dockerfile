FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Обучение модели и генерация результатов при сборке
RUN python scoring_engine.py

EXPOSE 5000

# gunicorn, not the Flask dev server -- debug=True in app.py's __main__ block
# is for local `python app.py` / `make run` only and never runs here, since
# gunicorn imports the `app` object directly.
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 app:app
