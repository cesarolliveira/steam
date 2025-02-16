ARG PYTHON_VERSION=3.9-slim

# Usa uma imagem Python como base
FROM python:${PYTHON_VERSION} AS consumer

ENV RABBITMQ_HOST=rabbitmq.steam.svc.cluster.local \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER=user \
    RABBITMQ_PASS=steam@2025 \
    RABBITMQ_QUEUE=steam

WORKDIR /app

COPY resources/consumer/requirements.txt /app/requirements.txt
COPY resources/consumer/consumer.py /app/consumer.py

# Instala dependências
RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]

# Usa uma imagem Python como base
FROM python:${PYTHON_VERSION} AS producer

ENV RABBITMQ_HOST=rabbitmq.steam.svc.cluster.local \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USER=user \
    RABBITMQ_PASS=steam@2025 \
    RABBITMQ_QUEUE=steam

# Instala dependências
RUN pip install pandas pika

# Copia o código e o arquivo CSV para o contêiner
COPY resources/producer/producer.py /app/producer.py
COPY temperature.csv /dados.csv

WORKDIR /app

# Comando para executar o serviço
CMD ["python", "producer.py", "echo 'Processo finalizado'"]

# Base Image
FROM python:${PYTHON_VERSION} AS streamlit

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos para o container
COPY resources/streamlit/app.py ./
COPY data/result.json ./

# Instalar dependências
RUN pip install streamlit pandas
RUN pip install streamlit matplotlib
RUN pip install streamlit seaborn
# Expôr a porta
EXPOSE 8501

# Comando de inicialização
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]
