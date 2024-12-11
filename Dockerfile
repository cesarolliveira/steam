ARG PYTHON_VERSION=3.9-slim

# Usa uma imagem Python como base
FROM python:${PYTHON_VERSION} AS consumer

WORKDIR /app

COPY resources/consumer/requirements.txt /app/requirements.txt
COPY resources/consumer/consumer.py /app/consumer.py

# Instala dependências
RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]

# Usa uma imagem Python como base
FROM python:${PYTHON_VERSION} AS producer

# Instala dependências
RUN pip install pandas pika

# Copia o código e o arquivo CSV para o contêiner
COPY resources/producer/producer.py /app/producer.py
COPY temperature.csv /dados.csv

WORKDIR /app

# Comando para executar o serviço
CMD ["python", "producer.py", "echo 'Processo finalizado'"] 