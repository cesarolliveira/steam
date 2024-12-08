# Usa uma imagem Python como base
FROM python:3.9-slim

WORKDIR /app

COPY resources/consumer/requirements.txt /app/requirements.txt
COPY resources/consumer/consumer.py /app/consumer.py

# Instala dependências
RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]
