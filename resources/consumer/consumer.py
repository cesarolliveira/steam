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
from collections import defaultdict
import ujson
import zipfile

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
BATCH_SIZE = 50          # Máximo de mensagens por lote
MIN_BATCH_SIZE = 25      # Mínimo de mensagens para processamento
FLUSH_INTERVAL = 5       # Segundos entre flushes

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
# VARIÁVEIS GLOBAIS DO PROCESSAMENTO
# ==============================================
buffer = defaultdict(list)  # {sensor: [(stats, delivery_tag)]}
last_flush = time.time()

# ==============================================
# GERENCIAMENTO DE ARQUIVOS E BUFFER
# ==============================================
def split_and_zip_large_file(file_path, max_size=5*1024*1024):
    """Divide e zipa arquivos maiores que o tamanho especificado"""
    try:
        file_size = os.path.getsize(file_path)
        if file_size <= max_size:
            return

        logger.info(f"Arquivo {file_path} excedeu 5MB. Iniciando divisão e compactação...")
        
        with open(file_path, 'r') as f:
            data = ujson.load(f)

        part_num = 1
        current_chunk = {}
        current_size = 0

        # Ordena os sensores para garantir consistência
        for sensor in sorted(data.keys()):
            sensor_data = {sensor: data[sensor]}
            sensor_json = ujson.dumps(sensor_data)
            sensor_size = len(sensor_json)

            # Verifica se precisa iniciar um novo chunk
            if current_size + sensor_size > max_size and current_chunk:
                # Escreve o chunk atual
                part_filename = f"{file_path}_part{part_num}"
                with open(part_filename, 'w') as part_file:
                    ujson.dump(current_chunk, part_file)
                
                # Zip e remove o arquivo original
                with zipfile.ZipFile(f"{part_filename}.zip", 'w') as zf:
                    zf.write(part_filename, arcname=os.path.basename(part_filename))
                os.remove(part_filename)
                
                part_num += 1
                current_chunk = {}
                current_size = 0

            # Adiciona ao chunk atual
            current_chunk.update(sensor_data)
            current_size += sensor_size

        # Escreve o último chunk
        if current_chunk:
            part_filename = f"{file_path}_part{part_num}"
            with open(part_filename, 'w') as part_file:
                ujson.dump(current_chunk, part_file)
            
            with zipfile.ZipFile(f"{part_filename}.zip", 'w') as zf:
                zf.write(part_filename, arcname=os.path.basename(part_filename))
            os.remove(part_filename)

        # Cria novo arquivo vazio
        with open(file_path, 'w') as f:
            f.write('{}')

        logger.info(f"Arquivo {file_path} dividido em {part_num} partes zipadas")

        # Gerenciar arquivos ZIP para manter até 10
        zip_files = []
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith('.zip'):
                file_path_zip = os.path.join(OUTPUT_DIR, f)
                mod_time = os.path.getmtime(file_path_zip)
                zip_files.append((mod_time, file_path_zip))
        
        # Ordenar do mais antigo para o mais novo
        zip_files.sort(key=lambda x: x[0])
        
        # Remover excedentes mantendo apenas os 10 mais recentes
        while len(zip_files) > 10:
            oldest = zip_files.pop(0)
            try:
                os.remove(oldest[1])
                logger.info(f"Arquivo ZIP {oldest[1]} removido para manter limite de 10 arquivos")
            except Exception as e:
                logger.error(f"Erro ao remover arquivo ZIP {oldest[1]}: {str(e)}")

    except Exception as e:
        logger.error(f"Erro ao dividir/zipar arquivo: {str(e)}")

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
                passive=True
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
    """Calcula estatísticas e detecta outliers com base em 10% da média"""
    try:
        arr = np.array(readings)
        stats = {
            'mean': round(float(np.mean(arr)), 2),
            'median': round(float(np.median(arr)), 2),
            'min': round(float(np.min(arr)), 2),
            'max': round(float(np.max(arr)), 2),
            'std_dev': round(float(np.std(arr)), 2),
            'q1': round(float(np.percentile(arr, 25)), 2),
            'q3': round(float(np.percentile(arr, 75)), 2)
        }

        mean_val = stats['mean']
        lower_bound = round(mean_val * 0.9, 2)
        upper_bound = round(mean_val * 1.1, 2)

        stats.update({
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'allowed_variation': 10
        })

        outliers = {}
        for idx, temp in enumerate(readings):
            if temp < lower_bound or temp > upper_bound:
                outliers[str(uuid.uuid4())] = {
                    'value': temp,
                    'timestamp': datetime.now().isoformat(),
                    'deviation': round(abs(temp - mean_val) / mean_val * 100, 2)
                }

        stats['outliers'] = outliers
        stats['total_outliers'] = len(outliers)
        return stats

    except Exception as e:
        logger.error(f"Erro no cálculo estatístico: {str(e)}")
        return {}

# ==============================================
# GERENCIAMENTO DE ARQUIVOS E BUFFER
# ==============================================
def flush_buffer(channel, force=False):
    global last_flush, buffer
    now = time.time()
    current_total = sum(len(v) for v in buffer.values())
    
    # Lógica de controle do flush
    if not force:
        if current_total < BATCH_SIZE and (now - last_flush < FLUSH_INTERVAL or current_total < MIN_BATCH_SIZE):
            return
    
    last_flush = now
    current_buffer = buffer.copy()
    buffer.clear()
    
    if not current_buffer:
        return

    try:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        lock = FileLock(LOCK_FILE, timeout=120)
        
        with lock:
            data = {}
            if Path(OUTPUT_FILE).exists():
                with open(OUTPUT_FILE, 'r') as f:
                    data = ujson.load(f)
            
            delivery_tags = []
            for sensor, entries in current_buffer.items():
                stats_batch = [e[0] for e in entries]
                delivery_tags.extend([e[1] for e in entries])
                
                if sensor not in data:
                    data[sensor] = {}
                
                for stats in stats_batch:
                    batch_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
                    data[sensor][batch_id] = {
                        **stats,
                        'processing_time': datetime.now().isoformat(),
                        'outlier_method': 'percentage',
                        'outlier_params': {
                            'variation_percent': 10
                        }
                    }
            
            temp_file = f"{OUTPUT_FILE}.tmp"
            with open(temp_file, 'w') as f:
                ujson.dump(data, f, indent=2)
                
            os.replace(temp_file, OUTPUT_FILE)
            
            # Verifica tamanho e divide/zipa se necessário
            split_and_zip_large_file(OUTPUT_FILE)

            logger.info(f" Processamento no POD {os.uname().nodename}. - Salvo {sum(len(v) for v in current_buffer.values())} mensagens.")

            for tag in delivery_tags:
                channel.basic_ack(tag)
                
    except Exception as e:
        logger.error(f"Erro no flush: {str(e)}. Reenfileirando mensagens.")
        for sensor, entries in current_buffer.items():
            for entry in entries:
                try:
                    channel.basic_nack(entry[1], requeue=True)
                except Exception as nack_error:
                    logger.error(f"Erro ao reenfileirar: {str(nack_error)}")

# ==============================================
# PROCESSAMENTO DE MENSAGENS
# ==============================================
def process_message(channel, method, properties, body):
    """Processa mensagens e acumula no buffer"""
    try:
        message = ujson.loads(body.decode())
        sensor = message.get('sensor', 'unknown')
        readings = message.get('leituras', [])
        
        if not readings:
            raise ValueError("Mensagem sem dados de leitura")
            
        stats = calculate_statistics(readings)
        buffer[sensor].append( (stats, method.delivery_tag) )
        
        logger.debug(f"Mensagem acumulada para {sensor} | Buffer: {len(buffer[sensor])}")
        flush_buffer(channel)
        
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        channel.basic_nack(method.delivery_tag, requeue=True)

# ==============================================
# CONEXÃO E LOOP PRINCIPAL
# ==============================================
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
    channel.basic_qos(prefetch_count=BATCH_SIZE * 2)
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
            connection, channel = setup_connection()
            all_queues = filter_queues(get_rabbitmq_queues(), QUEUE_PREFIX)
            
            if not all_queues:
                logger.warning("Nenhuma fila encontrada. Verifique o prefixo.")
                time.sleep(30)
                continue
                
            setup_queues(channel, all_queues)
            logger.info(f"Monitorando {len(all_queues)} fila(s)")
            
            while True:
                channel.start_consuming()
                flush_buffer(channel, force=True)
                
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
            flush_buffer(channel, force=True)

if __name__ == "__main__":
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    main_loop()
