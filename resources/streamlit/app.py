import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
import shutil

# Configuração da página
st.set_page_config(
    page_title="Elasteam",
    page_icon="🌡️",
    layout="wide"
)

caminho_arquivo = "/app/data/result.json"

# Função para carregar e exibir dados JSON
def carregar_dados_json(caminho_arquivo):
    temp_caminho = "/app/data/temp_result.json"  # Caminho temporário para contornar o bloqueio
    try:
        # Copiar o arquivo para um local temporário
        shutil.copy(caminho_arquivo, temp_caminho)

        # Ler o arquivo JSON copiado
        with open(temp_caminho, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo JSON: {e}")
        return None

# Função para detectar outliers usando o método IQR
def detectar_outliers(df):
    Q1 = df['Temperature'].quantile(0.25)
    Q3 = df['Temperature'].quantile(0.75)
    IQR = Q3 - Q1
    limite_inferior = Q1 - 1.5 * IQR
    limite_superior = Q3 + 1.5 * IQR

    # Identificar os outliers
    outliers = df[(df['Temperature'] < limite_inferior) | (df['Temperature'] > limite_superior)]
    
    return outliers, limite_inferior, limite_superior

# Carregar dados
data = carregar_dados_json(caminho_arquivo)

# Verificar se os dados foram carregados corretamente
if data is not None:
    st.write("Dados carregados com sucesso!")

    if isinstance(data, list):
        st.write(f"Primeiros itens da lista: {data[:5]}")

        temperaturas_termais = []
        for item in data:
            if isinstance(item, dict) and 'value' in item:
                try:
                    temp_value = float(item['value'])
                    temperaturas_termais.append(temp_value)
                except ValueError:
                    continue

        if temperaturas_termais:
            df_termal = pd.DataFrame(temperaturas_termais, columns=["Temperature"])
            st.title("Gráfico de Temperaturas Térmicas")

            outliers, limite_inferior, limite_superior = detectar_outliers(df_termal)

            plt.figure(figsize=(10, 6))
            sns.boxplot(data=df_termal, x='Temperature', color='skyblue', fliersize=7,
                        flierprops=dict(markerfacecolor='r', marker='o', markersize=7))

            plt.title("Distribuição das Temperaturas Térmicas")
            plt.xlabel("Temperatura Térmica (°C)")

            outlier_handle = plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='r', markersize=7)
            boxplot_handle = plt.Line2D([0], [0], color='skyblue', lw=4)

            plt.legend(handles=[boxplot_handle, outlier_handle],
                       labels=["Temperatura", "Outliers"], title="Categorias", loc="upper right")

            st.pyplot(plt)

            st.write(f"Outliers detectados: {len(outliers)}")
            if not outliers.empty:
                st.write("Outliers:")
                st.write(outliers)

        else:
            st.warning("Nenhuma temperatura térmica válida encontrada.")

        if data:
            first_item = data[0]
            st.write(f"Temperatura média: {first_item.get('mean', 'N/A')}°C")
            st.write(f"Temperatura mínima: {first_item.get('min', 'N/A')}°C")
            st.write(f"Temperatura máxima: {first_item.get('max', 'N/A')}°C")

    else:
        st.error(f"A estrutura dos dados não é válida. Tipo recebido: {type(data)}.")
else:
    st.error("Não foi possível carregar os dados do arquivo JSON.")