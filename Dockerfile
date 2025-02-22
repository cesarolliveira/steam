ARG PYTHON_VERSION=3.9-slim

# ==============================================
# CONSUMER
# ==============================================

FROM python:${PYTHON_VERSION} AS consumer

WORKDIR /app

COPY resources/consumer/requirements.txt /app/requirements.txt
COPY resources/consumer/consumer.py /app/consumer.py

RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]

# ==============================================
# PRODUCER
# ==============================================

FROM python:${PYTHON_VERSION} AS producer

RUN pip install pika

COPY resources/producer/producer.py /app/producer.py

WORKDIR /app

CMD ["python", "producer.py"]

# ==============================================
# STREAMLIT
# ==============================================

FROM python:${PYTHON_VERSION} AS streamlit

WORKDIR /app

COPY resources/streamlit/app.py /app/app.py
COPY resources/streamlit/requirements.txt /app/requirements.txt
COPY data/result.json /app/data/result.json

RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]
