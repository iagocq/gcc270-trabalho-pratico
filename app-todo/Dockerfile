FROM python:3.12-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY app.py .

CMD uvicorn app:app --host 0.0.0.0 --port 8000
