import os
import pandas as pd
import pika
import json
import time
import logging

# Configuração do RabbitMQ usando variáveis de ambiente
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq.steam.svc.cluster.local')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'steam')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'steam@2025')

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def connect_to_rabbitmq():
    """Conecta ao RabbitMQ com tratamento de erro e reconexão."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials,
        connection_attempts=3,
        retry_delay=5
    )

    for attempt in range(3):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Não redeclara a fila - assume que já existe
            # (a política 'lazy' já está configurada no servidor)
            return connection, channel
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Tentativa {attempt+1}/3 falhou: {str(e)}")
            if attempt < 2:
                time.sleep(2 ** attempt)
    
    raise Exception("Não foi possível conectar ao RabbitMQ após 3 tentativas")

def send_message(channel, message):
    """Envia uma mensagem JSON para a fila RabbitMQ com confirmação."""
    try:
        channel.basic_publish(
            exchange='',
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Mensagem persistente
                content_type='application/json'
            )
        )
        logger.info(f"Mensagem enviada: {message}")
    except pika.exceptions.UnroutableError:
        logger.error("Mensagem não pôde ser roteada")
    except pika.exceptions.ChannelClosed:
        logger.error("Canal fechado durante o envio")

def read_csv_and_send_to_rabbitmq(file_path):
    """Lê um arquivo CSV e envia os dados para o RabbitMQ."""
    try:
        data = pd.read_csv(file_path)
        logger.info(f"CSV carregado com {len(data)} registros")
        
        connection, channel = connect_to_rabbitmq()
        
        for _, row in data.iterrows():
            message = row.to_dict()
            try:
                send_message(channel, message)
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem: {str(e)}")
                # Tenta reconectar
                connection.close()
                connection, channel = connect_to_rabbitmq()
        
        logger.info("Todos os dados foram enviados")
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {file_path}")
    except pd.errors.EmptyDataError:
        logger.error("Arquivo CSV vazio ou inválido")
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()
            logger.info("Conexão fechada")

if __name__ == "__main__":
    file_path = '/dados.csv'
    read_csv_and_send_to_rabbitmq(file_path)