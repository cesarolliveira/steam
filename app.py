import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(
    page_title="Elasteam",  # Título da página no navegador
    page_icon="🌡️",  # Ícone que aparecerá na aba do navegador (pode ser um emoji ou um caminho de imagem)
    layout="wide"  # Layout da página
)

# Função para carregar e exibir dados JSON
def carregar_dados_json(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r') as file:
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
data = carregar_dados_json('result.json')

# Verificar se os dados foram carregados corretamente
if data is not None:
    # Exibir uma mensagem mais amigável sobre a estrutura dos dados
    st.write("Dados carregados com sucesso!")

    # Se `data` for uma lista, vamos inspecionar seus primeiros elementos
    if isinstance(data, list):
        st.write(f"Primeiros itens da lista: {data[:5]}")  # Mostrar os primeiros 5 itens da lista

        # Agora, vamos processar os dados e criar o gráfico
        temperaturas_termais = []  # Lista para armazenar as temperaturas térmicas
        for item in data:
            if isinstance(item, dict) and 'value' in item:
                # Convertendo o valor de temperatura térmica para float
                try:
                    temp_value = float(item['value'])
                    temperaturas_termais.append(temp_value)
                except ValueError:
                    continue  # Se não for possível converter, ignore esse item

        if temperaturas_termais:
            # Criando o DataFrame a partir das temperaturas térmicas
            df_termal = pd.DataFrame(temperaturas_termais, columns=["Temperature"])
            df_termal["Time"] = range(len(df_termal))

            st.title("Gráfico de Temperaturas Térmicas")

            # Detectando outliers
            outliers, limite_inferior, limite_superior = detectar_outliers(df_termal)

            # Plotando o gráfico de temperatura térmica com Matplotlib
            plt.figure(figsize=(10, 6))
            plt.plot(df_termal["Time"], df_termal["Temperature"], color='b', label="Temperatura", alpha=0.7)
            plt.scatter(outliers["Time"], outliers["Temperature"], color='r', label="Outliers", zorder=5)
            plt.title("Temperatura Térmica ao longo do tempo com Outliers")
            plt.xlabel("Tempo")
            plt.ylabel("Temperatura Térmica (°C)")
            plt.grid(True)
            plt.legend()

            # Exibir o gráfico no Streamlit
            st.pyplot(plt)

            # Exibindo informações sobre os outliers
            st.write(f"Outliers detectados: {len(outliers)}")
            if not outliers.empty:
                st.write("Outliers:")
                st.write(outliers)

        else:
            st.warning("Nenhuma temperatura térmica válida encontrada.")

        # Exibindo estatísticas de temperatura
        if data:
            first_item = data[0]  # Pegar o primeiro item para estatísticas gerais
            st.write(f"Temperatura média: {first_item.get('mean', 'N/A')}°C")
            st.write(f"Temperatura mínima: {first_item.get('min', 'N/A')}°C")
            st.write(f"Temperatura máxima: {first_item.get('max', 'N/A')}°C")

    else:
        st.error(f"A estrutura dos dados não é válida. Tipo recebido: {type(data)}. Esperávamos uma lista.")
else:
    st.error("Não foi possível carregar os dados do arquivo JSON.")
