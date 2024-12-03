# Usa uma imagem Python como base
FROM python:3.9-slim

# Instala dependências
RUN pip install pandas pika

# Copia o código e o arquivo CSV para o contêiner
COPY resources/producer/producer.py /app/producer.py
COPY temperature.csv /dados.csv

WORKDIR /app

# Comando para executar o serviço
CMD ["python", "producer.py"]