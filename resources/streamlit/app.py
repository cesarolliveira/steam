import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
import shutil
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Elasteam Analytics",
    page_icon="🌡️",
    layout="wide"
)

caminho_arquivo = "/app/data/result.json"

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
            # Parse da data do batch_id (formato: %Y%m%d%H%M%S)
            timestamp = datetime.strptime(batch_id.split('_')[0], "%Y%m%d%H%M%S")
            
            processed.append({
                "sensor": sensor,
                "batch_id": batch_id,
                "timestamp": timestamp,
                "mean": stats['mean'],
                "median": stats['median'],
                "min": stats['min'],
                "max": stats['max'],
                "std_dev": stats['std_dev'],
                "q1": stats['q1'],
                "q3": stats['q3'],
                "total_outliers": stats['total_outliers'],
                "outlier_method": stats['outlier_method'],
                "processing_time": stats['processing_time']
            })
    
    return pd.DataFrame(processed)

def plot_series_temporais(df, sensor):
    """Cria gráficos de série temporal para um sensor específico"""
    df_filtered = df[df['sensor'] == sensor].sort_values('timestamp')
    
    fig, ax = plt.subplots(2, 1, figsize=(12, 10))
    
    # Gráfico de Média com faixa de variação e quartis
    sns.lineplot(data=df_filtered, x='timestamp', y='mean', ax=ax[0], label='Média', color='blue')
    sns.lineplot(data=df_filtered, x='timestamp', y='q1', ax=ax[0], label='Q1', color='green', linestyle='--')
    sns.lineplot(data=df_filtered, x='timestamp', y='q3', ax=ax[0], label='Q3', color='orange', linestyle='--')
    
    ax[0].fill_between(df_filtered['timestamp'], 
                      df_filtered['min'], 
                      df_filtered['max'], 
                      color='blue', alpha=0.1)
    
    ax[0].set_title(f'Evolução Temporal - {sensor}')
    ax[0].set_ylabel('Temperatura (°C)')
    ax[0].legend(loc='upper left')
    
    # Gráfico de Outliers
    sns.barplot(data=df_filtered, x='timestamp', y='total_outliers', ax=ax[1], color='red')
    ax[1].set_title('Quantidade de Outliers por Lote')
    ax[1].set_ylabel('Número de Outliers')
    ax[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    return fig

def exibir_detalhes_batch(batch_data):
    """Exibe os detalhes estatísticos de um lote específico"""
    st.subheader("Estatísticas Detalhadas")
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("Média", f"{batch_data['mean']}°C")
        st.metric("Mediana", f"{batch_data['median']}°C")
    
    with cols[1]:
        st.metric("Mínima", f"{batch_data['min']}°C")
        st.metric("Máxima", f"{batch_data['max']}°C")
    
    with cols[2]:
        st.metric("Desvio Padrão", f"{batch_data['std_dev']}°C")
        st.metric("Outliers", batch_data['total_outliers'])
    
    with cols[3]:
        st.metric("Método de Detecção", batch_data['outlier_method'])
        st.metric("Q1/Q3", f"{batch_data['q1']}°C / {batch_data['q3']}°C")

# Interface principal
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
    
    # Sidebar com controles
    with st.sidebar:
        st.header("Filtros")
        
        # Seletor de sensor
        sensores = df['sensor'].unique()
        sensor_selecionado = st.selectbox("Selecione o Sensor", sensores)
        
        # Seletor de período
        datas = df['timestamp'].dt.date.unique()
        data_selecionada = st.selectbox("Selecione a Data", datas)
    
    # Filtrar dados
    df_filtrado = df[(df['sensor'] == sensor_selecionado) & 
                    (df['timestamp'].dt.date == data_selecionada)]
    
    # Layout principal
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Gráfico de série temporal
        st.pyplot(plot_series_temporais(df, sensor_selecionado))
    
    with col2:
        # Último lote processado
        ultimo_batch = df_filtrado.iloc[-1]
        st.subheader("Último Lote Processado")
        st.caption(f"ID: {ultimo_batch['batch_id']}")
        st.metric("Temperatura Média", f"{ultimo_batch['mean']}°C")
        st.metric("Outliers Detectados", ultimo_batch['total_outliers'])
    
    # Exibir detalhes do batch selecionado
    batches_disponiveis = df_filtrado['batch_id'].tolist()
    batch_selecionado = st.selectbox("Selecione um Lote para Detalhes", batches_disponiveis)
    
    if batch_selecionado:
        batch_data = raw_data[sensor_selecionado][batch_selecionado]
        exibir_detalhes_batch(batch_data)

if __name__ == "__main__":
    main()
