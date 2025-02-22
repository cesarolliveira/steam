import pika
import os
import json
import logging
import time
import requests
import numpy as np
import uuid
from datetime import datetime
from pathlib import Path
from filelock import FileLock

# ==============================================
# CONFIGURAÇÕES GLOBAIS (variáveis de ambiente)
# ==============================================
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq.steam.svc.cluster.local')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'steam@2025')
QUEUE_PREFIX = os.getenv('QUEUE_PREFIX', 'steam.TEMP_')
RABBITMQ_API_PORT = os.getenv('RABBITMQ_API_PORT', '15672')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/data')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'result.json')
LOCK_FILE = os.path.join(OUTPUT_DIR, 'result.lock')

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(OUTPUT_DIR, 'consumer.log'))
    ]
)
logger = logging.getLogger(__name__)

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================
def get_rabbitmq_queues():
    """Obtém lista de filas usando a API de gerenciamento do RabbitMQ"""
    try:
        response = requests.get(
            f'http://{RABBITMQ_HOST}:{RABBITMQ_API_PORT}/api/queues',
            auth=(RABBITMQ_USER, RABBITMQ_PASS),
            timeout=10
        )
        response.raise_for_status()
        return [queue['name'] for queue in response.json()]
    except Exception as e:
        logger.error(f"Erro ao obter filas: {str(e)}")
        return []

def filter_queues(queues, prefix):
    """Filtra filas pelo prefixo especificado"""
    return [q for q in queues if q.startswith(prefix)]

def setup_queues(channel, queues):
    """Configura o consumo para as filas especificadas"""
    for queue in queues:
        try:
            channel.queue_declare(
                queue=queue,
                durable=True,
                passive=True  # Apenas verifica se a fila existe
            )
            channel.basic_consume(
                queue=queue,
                on_message_callback=process_message,
                auto_ack=False
            )
            logger.info(f"Registrado na fila: {queue}")
        except pika.exceptions.ChannelClosedByBroker as e:
            logger.error(f"Erro na fila {queue}: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")

# ==============================================
# FUNÇÕES DE PROCESSAMENTO DE DADOS
# ==============================================
def calculate_statistics(readings):
    """Calcula estatísticas para um conjunto de leituras"""
    try:
        arr = np.array(readings)
        return {
            'mean': round(float(np.mean(arr)), 2),
            'min': round(float(np.min(arr)), 2),
            'max': round(float(np.max(arr)), 2),
            'std_dev': round(float(np.std(arr)), 2),
            'outliers': detect_outliers(readings)
        }
    except Exception as e:
        logger.error(f"Erro no cálculo estatístico: {str(e)}")
        return {}

def detect_outliers(readings):
    """Detecta outliers usando o método IQR"""
    try:
        if len(readings) < 4:
            return {}
            
        q1 = np.percentile(readings, 25)
        q3 = np.percentile(readings, 75)
        iqr = q3 - q1
        
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        
        return {
            str(idx): temp
            for idx, temp in enumerate(readings)
            if temp < lower or temp > upper
        }
    except Exception as e:
        logger.error(f"Erro na detecção de outliers: {str(e)}")
        return {}

# ==============================================
# GERENCIAMENTO DE ARQUIVOS
# ==============================================
def save_results(sensor, stats):
    """Salva resultados no arquivo JSON com lock"""
    try:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        lock = FileLock(LOCK_FILE, timeout=60)
        
        with lock:
            # Carrega dados existentes
            data = {}
            if Path(OUTPUT_FILE).exists():
                with open(OUTPUT_FILE, 'r') as f:
                    data = json.load(f)
            
            # Gera ID único para o lote
            batch_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
            
            # Estrutura de armazenamento
            if sensor not in data:
                data[sensor] = {}
                
            data[sensor][batch_id] = {
                **stats,
                'processing_time': datetime.now().isoformat(), # Data e hora do processamento
                'total_outliers': len(stats.get('outliers', {})) # Número de outliers
            }
            
            # Write to temporary file first
            temp_file = f"{OUTPUT_FILE}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Atomic replace
            os.replace(temp_file, OUTPUT_FILE)
            logger.info(f"Dados salvos para {sensor} | Lote: {batch_id}")
            
    except Exception as e:
        logger.error(f"Erro ao salvar dados: {str(e)}")
        raise

# ==============================================
# CONEXÃO E PROCESSAMENTO DE MENSAGENS
# ==============================================
def process_message(channel, method, properties, body):
    """Processa cada mensagem recebida"""
    try:
        # Decodifica a mensagem
        message = json.loads(body.decode())
        sensor = message.get('sensor', 'unknown')
        readings = message.get('leituras', [])
        
        if not readings:
            raise ValueError("Mensagem sem dados de leitura")
            
        logger.debug(f"Processando {len(readings)} leituras de {sensor}")
        
        # Calcula estatísticas
        stats = calculate_statistics(readings)
        
        # Salva resultados
        save_results(sensor, stats)
        
        # Confirma o processamento
        channel.basic_ack(delivery_tag=method.delivery_tag)
        
    except json.JSONDecodeError:
        logger.error("Mensagem com formato inválido")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def setup_connection():
    """Configura a conexão com o RabbitMQ"""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials,
        connection_attempts=3,
        retry_delay=10,
        heartbeat=30
    )
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.basic_qos(prefetch_count=20)
    return connection, channel

def main_loop():
    """Loop principal de execução"""
    logger.info(f"""
    Iniciando Consumer com configuração:
    - Host RabbitMQ: {RABBITMQ_HOST}
    - Prefixo das filas: {QUEUE_PREFIX}
    - Arquivo de saída: {OUTPUT_FILE}
    """)
    
    while True:
        connection = None
        try:
            # Estabelece conexão
            connection, channel = setup_connection()
            
            # Descobre e configura filas dinamicamente
            all_queues = get_rabbitmq_queues()
            target_queues = filter_queues(all_queues, QUEUE_PREFIX)
            
            if not target_queues:
                logger.warning("Nenhuma fila encontrada. Verifique o prefixo.")
                time.sleep(30)
                continue
                
            setup_queues(channel, target_queues)
            logger.info(f"Monitorando {len(target_queues)} fila(s)")
            
            # Inicia o consumo de mensagens
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            logger.error("Conexão perdida. Reconectando em 30 segundos...")
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Encerramento solicitado pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro não tratado: {str(e)}")
            time.sleep(10)
        finally:
            if connection and connection.is_open:
                connection.close()

if __name__ == "__main__":
    # Verifica/Cria diretório de saída
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    main_loop()
