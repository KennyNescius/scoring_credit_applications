FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Обучение модели и генерация результатов при сборке
RUN python scoring_engine.py

EXPOSE 5000

CMD ["python", "app.py"]
