import os
import pika
import json
import time
import logging
import random

# ==============================================
# CONFIGURAÇÃO DE LOGGING
# ==============================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================
# CONFIGURAÇÕES AJUSTÁVEIS (variáveis de ambiente)
# ==============================================
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq.steam.svc.cluster.local')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'steam')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'steam@2025')

NUM_SENSORES = int(os.getenv('NUM_SENSORES', 10))            
INTERVALO_COLETA = int(os.getenv('INTERVALO_COLETA', 1))    
TEMPERATURA_MIN = int(os.getenv('TEMPERATURA_MIN', 0))      
TEMPERATURA_MAX = int(os.getenv('TEMPERATURA_MAX', 100))    
NUM_LEITURAS = 60                                           

SENSORES = [f"TEMP_{i+1}" for i in range(NUM_SENSORES)]

sensor_states = {}
for sensor in SENSORES:
    media = (TEMPERATURA_MIN + TEMPERATURA_MAX) / 2
    sensor_states[sensor] = {
        'start_time': time.time(),
        'stabilization_time': random.randint(20, 30),
        'in_anomaly': False,
        'anomaly_start_time': None,
        'anomaly_duration': 0,
        'anomaly_type': None,
        'media': media
    }
logger.debug(f"Estados iniciais dos sensores: {json.dumps(sensor_states, indent=2)}")

def conectar_rabbitmq():
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
        for sensor in SENSORES:
            channel.queue_declare(
                queue=f'{RABBITMQ_QUEUE}.{sensor}',
                durable=True,
                arguments={'x-queue-mode': 'lazy'}
            )
        logger.info(f"Conexão estabelecida para {NUM_SENSORES} sensores")
        return connection, channel
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Falha na conexão: {str(e)}")
        raise

def enviar_lote_dados(channel, sensor):
    try:
        state = sensor_states[sensor]
        current_time = time.time()
        elapsed = current_time - state['start_time']
        media = state['media']

        if elapsed < state['stabilization_time']:
            progresso = elapsed / state['stabilization_time']
            temp_base = TEMPERATURA_MIN + (media - TEMPERATURA_MIN) * progresso
        else:
            if state['in_anomaly']:
                tempo_anomalia = current_time - state['anomaly_start_time']
                if tempo_anomalia >= state['anomaly_duration']:
                    state['in_anomaly'] = False
                    temp_base = media
                else:
                    temp_base = media + (TEMPERATURA_MAX - media) * 0.25 if state['anomaly_type'] == 'alta' else media - (media - TEMPERATURA_MIN) * 0.25
            else:
                if random.random() < 0.02:
                    state['in_anomaly'] = True
                    state['anomaly_start_time'] = current_time
                    state['anomaly_duration'] = random.randint(5, 15)
                    state['anomaly_type'] = random.choice(['alta', 'baixa'])
                    temp_base = media + (TEMPERATURA_MAX - media) * 0.25 if state['anomaly_type'] == 'alta' else media - (media - TEMPERATURA_MIN) * 0.25
                else:
                    temp_base = media + random.uniform(-2, 2)
        
        variacao = [round(temp_base + random.uniform(-1, 1), 2) for _ in range(NUM_LEITURAS)]
        lote_temperaturas = [max(TEMPERATURA_MIN, min(TEMPERATURA_MAX, temp)) for temp in variacao]
        
        logger.debug(f"Estado atualizado do sensor {sensor}: {json.dumps(state, indent=2)}")
        
        payload = {
            'sensor': sensor,
            'leituras': lote_temperaturas,
            'timestamp_inicio': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)),
            'intervalo': INTERVALO_COLETA,
            'unidade': 'Celsius'
        }
        
        channel.basic_publish(
            exchange='',
            routing_key=f'steam.{sensor}',
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        logger.info(f"Lote enviado: {sensor} | Leituras: {len(lote_temperaturas)}")
        logger.debug(f"Payload enviado: {json.dumps(payload, indent=2)}")
    except Exception as e:
        logger.error(f"Erro no envio para {sensor}: {str(e)}")
        raise

def simular_coleta():
    logger.info(f"Iniciando coleta de dados para {NUM_SENSORES} sensores")
    while True:
        try:
            connection, channel = conectar_rabbitmq()
            for sensor in SENSORES:
                enviar_lote_dados(channel, sensor)
            time.sleep(INTERVALO_COLETA)
        except pika.exceptions.AMQPConnectionError:
            logger.error("Erro de conexão, tentando novamente em 10 segundos...")
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Encerrando coleta...")
            if 'connection' in locals() and connection.is_open:
                connection.close()
            break
        except Exception as e:
            logger.error(f"Erro não tratado: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    simular_coleta()
