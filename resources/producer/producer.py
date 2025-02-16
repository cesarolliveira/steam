import os
import pandas as pd
import pika
import json

# Configuração do RabbitMQ usando variáveis de ambiente
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq.steam.svc.cluster.local')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'steam')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'steam@2025')

def connect_to_rabbitmq():
    """Conecta ao RabbitMQ e retorna o canal."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    return connection, channel

def send_message(channel, message):
    """Envia uma mensagem JSON para a fila RabbitMQ."""
    channel.basic_publish(
        exchange='',
        routing_key=RABBITMQ_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)  # mensagem persistente
    )
    print("Mensagem enviada:", message)

def read_csv_and_send_to_rabbitmq(file_path):
    """Lê um arquivo CSV e envia cada linha como uma mensagem JSON para a fila."""
    data = pd.read_csv(file_path)
    connection, channel = connect_to_rabbitmq()

    try:
        for _, row in data.iterrows():
            message = row.to_dict()
            send_message(channel, message)
    finally:
        connection.close()
        print("Conexão com RabbitMQ fechada.")

if __name__ == "__main__":
    file_path = '/dados.csv'  # Define o caminho do arquivo CSV na raiz do contêiner
    read_csv_and_send_to_rabbitmq(file_path)