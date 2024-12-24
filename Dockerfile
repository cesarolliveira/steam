ARG PYTHON_VERSION=3.9-slim

# Usa uma imagem Python como base
FROM python:${PYTHON_VERSION} AS consumer-amd64
WORKDIR /app

COPY resources/consumer/requirements.txt /app/requirements.txt
COPY resources/consumer/consumer.py /app/consumer.py

# Instala dependências
RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]

# Usa uma imagem Python como base
FROM python:${PYTHON_VERSION} AS producer-amd64

# Instala dependências
RUN pip install pandas pika

# Copia o código e o arquivo CSV para o contêiner
COPY resources/producer/producer.py /app/producer.py
COPY temperature.csv /dados.csv

WORKDIR /app

# Comando para executar o serviço
CMD ["python", "producer.py", "echo 'Processo finalizado'"]

# Base Image
FROM python:${PYTHON_VERSION} AS streamlit-amd64

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

#####################################################################################

# Usa uma imagem Python como base
FROM arm64v8/python:${PYTHON_VERSION} AS consumer-arm64

WORKDIR /app

COPY resources/consumer/requirements.txt /app/requirements.txt
COPY resources/consumer/consumer.py /app/consumer.py

# Instala dependências
RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]

# Usa uma imagem Python como base
FROM arm64v8/python:${PYTHON_VERSION} AS producer-arm64

# Instala dependências
RUN pip install pandas pika

# Copia o código e o arquivo CSV para o contêiner
COPY resources/producer/producer.py /app/producer.py
COPY temperature.csv /dados.csv

WORKDIR /app

# Comando para executar o serviço
CMD ["python", "producer.py", "echo 'Processo finalizado'"]

# Base Image
FROM arm64v8/python:${PYTHON_VERSION} AS streamlit-arm64

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos para o container
COPY resources/streamlit/app.py ./

# Instalar dependências
RUN pip install streamlit pandas
RUN pip install streamlit matplotlib
RUN pip install streamlit seaborn
# Expôr a porta
EXPOSE 8501

# Comando de inicialização
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]
