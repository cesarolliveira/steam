import os
import pika
import json
import time
import logging
import random

# ==============================================
# CONFIGURAÇÕES AJUSTÁVEIS (variáveis de ambiente)
# ==============================================
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq.steam.svc.cluster.local')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'steam')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'steam@2025')


NUM_SENSORES = int(os.getenv('NUM_SENSORES', 5))            # Quantidade de sensores
INTERVALO_COLETA = int(os.getenv('INTERVALO_COLETA', 1))     # Intervalo em segundos
TEMPERATURA_MIN = int(os.getenv('TEMPERATURA_MIN', -5))      # Mínimo de temperatura
TEMPERATURA_MAX = int(os.getenv('TEMPERATURA_MAX', 100))     # Máximo de temperatura
NUM_LEITURAS = 60                                           # Leituras por intervalo

# Gera lista dinâmica de sensores
SENSORES = [f"TEMP_{i+1}" for i in range(NUM_SENSORES)]

# ==============================================
# CONFIGURAÇÃO DE LOGGING
# ==============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================
# FUNÇÕES PRINCIPAIS
# ==============================================
def conectar_rabbitmq():
    """Estabelece conexão com o RabbitMQ e cria as filas necessárias."""
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials,
            connection_attempts=3,
            retry_delay=5
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Cria fila para cada sensor
        for sensor in SENSORES:
            channel.queue_declare(
                queue=f'{RABBITMQ_QUEUE}.{sensor}',
                durable=True,
                arguments={
                    'x-queue-mode': 'lazy',
                    'x-max-length': 10000
                }
            )
        
        logger.info(f"Conexão estabelecida para {NUM_SENSORES} sensores")
        return connection, channel
    
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Falha na conexão: {str(e)}")
        raise

def gerar_lote_temperaturas():
    """Gera um lote de 100 temperaturas aleatórias."""
    return [round(random.uniform(TEMPERATURA_MIN, TEMPERATURA_MAX), 2) for _ in range(NUM_LEITURAS)]

def enviar_lote_dados(channel, sensor):
    """Envia um lote de dados para a fila do sensor."""
    try:
        lote_temperaturas = gerar_lote_temperaturas()
        payload = {
            'sensor': sensor,
            'leituras': lote_temperaturas,
            'timestamp_inicio': time.strftime('%Y-%m-%d %H:%M:%S'),
            'intervalo': INTERVALO_COLETA,
            'unidade': 'Celsius'
        }
        
        channel.basic_publish(
            exchange='',
            routing_key=f'steam.{sensor}',
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json',
                content_encoding='utf-8'
            )
        )
        logger.info(f"Lote enviado: {sensor} | Leituras: {len(lote_temperaturas)} | Exemplo: {lote_temperaturas[:2]}...{lote_temperaturas[-2:]}")
    
    except Exception as e:
        logger.error(f"Erro no envio para {sensor}: {str(e)}")
        raise

def simular_coleta():
    """Rotina principal de coleta de dados."""
    logger.info(f"""Iniciando coleta:
    - Sensores: {NUM_SENSORES}
    - Leituras por intervalo: {NUM_LEITURAS}
    - Intervalo: {INTERVALO_COLETA}s
    - Faixa térmica: {TEMPERATURA_MIN}°C a {TEMPERATURA_MAX}°C""")
    
    while True:
        inicio_ciclo = time.time()
        try:
            connection, channel = conectar_rabbitmq()
            
            # Envia lote para todos os sensores
            for sensor in SENSORES:
                enviar_lote_dados(channel, sensor)
            
            # Controle preciso do intervalo
            tempo_decorrido = time.time() - inicio_ciclo
            tempo_espera = max(INTERVALO_COLETA - tempo_decorrido, 0)
            time.sleep(tempo_espera)
            
        except pika.exceptions.AMQPConnectionError:
            logger.error("Reconectando em 10 segundos...")
            time.sleep(10)
            
        except KeyboardInterrupt:
            logger.info("Encerrando coleta...")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            break
            
        except Exception as e:
            logger.error(f"Erro não tratado: {str(e)}")
            time.sleep(5)

# ==============================================
# EXECUÇÃO PRINCIPAL
# ==============================================
if __name__ == "__main__":
    simular_coleta()
