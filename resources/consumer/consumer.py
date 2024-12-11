import pika
import os
import json
import logging
from pathlib import Path
import time  # Para aguardar um intervalo entre as verificações da fila

# Configuração do RabbitMQ usando variáveis de ambiente
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq.steam.svc.cluster.local')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'steam')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', '123456789')

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Caminho do arquivo JSON
OUTPUT_FILE = "result.json"
BATCH_SIZE = 1000  # Número de mensagens por lote

# Função para conectar ao RabbitMQ e declarar a fila
def connect_to_rabbitmq():
    # Configurando as credenciais e parâmetros de conexão
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    connection_params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,  # Porta padrão do RabbitMQ
        credentials=credentials
    )

    # Conectando ao RabbitMQ
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()

    # Declarar a fila
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

    return connection, channel

# Função para salvar mensagens em um arquivo JSON formatado
def salvar_mensagens_em_json(mensagens):
    # Carregar dados existentes, se o arquivo existir
    dados = []
    if Path(OUTPUT_FILE).is_file():
        with open(OUTPUT_FILE, "r") as f:
            dados = json.load(f)
    
    # Adicionar as novas mensagens
    dados.extend(mensagens)
    
    # Salvar as mensagens no arquivo JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(dados, f, indent=4)
    logger.info(f"Lote de {len(mensagens)} mensagens salvo em {OUTPUT_FILE}")

# Função para processar mensagens em lotes
def processar_lote(channel):
    mensagens = []
    for _ in range(BATCH_SIZE):
        method_frame, properties, body = channel.basic_get(queue=RABBITMQ_QUEUE, auto_ack=False)
        if method_frame:
            message = json.loads(body.decode())
            # prepara dados
            preparar_dados(message)
            mensagens.append(message)
            # Acknowledge a mensagem
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        else:
            logger.info("Nenhuma mensagem restante na fila.")
            break
    
    if mensagens:
        salvar_mensagens_em_json(mensagens)
        logger.info(f"Lote de {len(mensagens)} mensagens processado.")
    else:
        logger.info("Nenhuma mensagem para processar.")

# Conectar ao RabbitMQ
connection, channel = connect_to_rabbitmq()

def preparar_dados(message):
    # A mensagem já é um dicionário, então não é necessário substituir as aspas
    keys = message.keys()
    values = message.values()

    # Dividindo a chave e o valor em listas
    keys_split = list(keys)[0].split(';')  # 'TEMP_1;TEMP_2;TEMP_3;TEMP_4;TEMP_5'
    values_split = list(values)[0].split(';')  # '23.80;31.74;47.23;24.78;28.64'

    # Criando um novo dicionário com o formato correto
    formatted_data = {f"temp_{i+1}": values_split[i] for i in range(len(keys_split))}

    # Gerando o JSON formatado
    formatted_json = json.dumps(formatted_data, indent=4)
    print(formatted_json)

try:
    while True:
        logger.info(f"Processando lote de até {BATCH_SIZE} mensagens...")
        processar_lote(channel)
        
        # Aguarda por 2 segundos antes de verificar a fila novamente (ajustável conforme necessário)
        time.sleep(2)  # Pode ajustar esse tempo para controlar a frequência da verificação da fila

except KeyboardInterrupt:
    logger.info("Interrompido pelo usuário.")
