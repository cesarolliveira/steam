# Base Image
FROM python:3.9-slim

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos para o container
COPY app.py ./
COPY result.json ./

# Instalar dependências
RUN pip install streamlit pandas
RUN pip install streamlit matplotlib

# Expôr a porta
EXPOSE 8501

# Comando de inicialização
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]
