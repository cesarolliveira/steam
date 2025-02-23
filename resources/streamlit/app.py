import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Elasteam Analytics",
    page_icon="🌡️",
    layout="wide"
)

caminho_arquivo = "/app/data/result.json"

# Variável para definir a quantidade de lotes para média histórica
NUM_LOTES_HISTORICO = 30

# Definição de intervalos de tempo para filtro
INTERVALOS_TEMPO = {
    "Últimos 30 segundos": timedelta(seconds=30),
    "Últimos 1 minuto": timedelta(minutes=1),
    "Últimos 3 minutos": timedelta(minutes=3),
    "Últimos 5 minutos": timedelta(minutes=5)
}

def carregar_dados_json(caminho_arquivo):
    """Carrega os dados do arquivo JSON com tratamento de erros"""
    try:
        with open(caminho_arquivo, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo JSON: {e}")
        return None

def processar_dados(data):
    """Processa os dados brutos do JSON para um formato estruturado"""
    processed = []
    
    for sensor, batches in data.items():
        for batch_id, stats in batches.items():
            try:
                timestamp = datetime.strptime(batch_id.split('_')[0], "%Y%m%d%H%M%S")
                
                processed.append({
                    "sensor": sensor,
                    "batch_id": batch_id,
                    "timestamp": timestamp,
                    "mean": stats['mean'],
                    "min": stats['min'],
                    "max": stats['max'],
                    "total_outliers": stats['total_outliers']
                })
            except KeyError as e:
                st.warning(f"Campo faltando no lote {batch_id}: {e}")
    
    df = pd.DataFrame(processed)
    if not df.empty:
        df['mean_historica'] = df['mean'].rolling(NUM_LOTES_HISTORICO, min_periods=1).mean()
        df['std_historico'] = df['mean'].rolling(NUM_LOTES_HISTORICO, min_periods=1).std()
        df['lower_bound'] = df['mean_historica'] - df['std_historico']
        df['upper_bound'] = df['mean_historica'] + df['std_historico']
        df['variacao'] = df['mean'].diff()
    
    return df

def plot_series_temporais(df, sensor):
    """Cria gráficos de série temporal com destaque para outliers"""
    df_filtered = df[df['sensor'] == sensor].sort_values('timestamp')
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Gráfico Principal
    sns.lineplot(data=df_filtered, x='timestamp', y='mean_historica', ax=ax, label='Média', color='blue')
    sns.lineplot(data=df_filtered, x='timestamp', y='min', ax=ax, label='Mínima', color='green', linestyle='--')
    sns.lineplot(data=df_filtered, x='timestamp', y='max', ax=ax, label='Máxima', color='red', linestyle='--')
    ax.plot(df_filtered['timestamp'], df_filtered['lower_bound'], '--', color='gray', label='Limite Inferior')
    ax.plot(df_filtered['timestamp'], df_filtered['upper_bound'], '--', color='gray', label='Limite Superior')
    ax.fill_between(df_filtered['timestamp'], df_filtered['lower_bound'], df_filtered['upper_bound'], color='green', alpha=0.1)
    
    # Detecta e marca outliers
    mask_outliers = (df_filtered['min'] < df_filtered['lower_bound']) | (df_filtered['max'] > df_filtered['upper_bound'])
    sns.scatterplot(data=df_filtered[mask_outliers], x='timestamp', y='min', ax=ax, color='red', marker='X', s=100, label='Outliers')
    sns.scatterplot(data=df_filtered[mask_outliers], x='timestamp', y='max', ax=ax, color='red', marker='X', s=100)
    
    ax.set_title(f'Evolução Temporal - {sensor}')
    ax.set_ylabel('Temperatura (°C)')
    ax.legend(loc='upper left')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def plot_variacao(df):
    """Cria gráfico específico para variação da temperatura"""
    fig, ax = plt.subplots(figsize=(14, 3))
    
    sns.lineplot(data=df, x='timestamp', y='variacao', ax=ax, color='purple')
    ax.axhline(0, color='gray', linestyle='--')
    ax.set_title('Variação da Temperatura ao Longo do Tempo')
    ax.set_ylabel('Variação (°C)')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def main():
    st.title("Dashboard de Monitoramento Térmico")
    
    # Carregar dados
    raw_data = carregar_dados_json(caminho_arquivo)
    
    if raw_data is None:
        return
    
    # Processar dados
    df = processar_dados(raw_data)
    
    if df.empty:
        st.warning("Nenhum dado disponível para análise.")
        return
    
    with st.sidebar:
        st.header("Controles")
        sensor_selecionado = st.selectbox("Sensor", df['sensor'].unique())
        data_selecionada = st.date_input("Data", df['timestamp'].max())
        intervalo_tempo = st.selectbox("Período", list(INTERVALOS_TEMPO.keys()))
    
    tempo_limite = datetime.now() - INTERVALOS_TEMPO[intervalo_tempo]
    
    df_filtrado = df[
        (df['sensor'] == sensor_selecionado) &
        (df['timestamp'].dt.date == data_selecionada) &
        (df['timestamp'] >= tempo_limite)
    ]
    
    if not df_filtrado.empty:
        st.pyplot(plot_series_temporais(df_filtrado, sensor_selecionado))
        
        st.subheader("Análise de Variação Térmica")
        st.pyplot(plot_variacao(df_filtrado))
    else:
        st.warning("Nenhum dado disponível para o período selecionado")

if __name__ == "__main__":
    main()
