import streamlit as st
import pandas as pd
from pathlib import Path
from motor_rag import MotorRAG

st.set_page_config(page_title="Explorador de Dados", page_icon="📊", layout="wide")

st.title("📊 Explorador de Acórdãos")
st.caption("Filtre, analise e exporte os dados indexados pelo sistema.")

@st.cache_data(show_spinner=False)
def carregar_dados():
    motor = MotorRAG()
    try:
        motor.inicializar()
        if motor.documentos:
            # Extrair os metadados dos documentos (ignorando o chunk inteiro pra UI ficar leve)
            metas = [doc["metadados"] for doc in motor.documentos]
            return pd.DataFrame(metas)
        return pd.DataFrame()
    except Exception as e:
        return None

df = carregar_dados()

if df is not None and not df.empty:
    st.success(f"Carregados {len(df)} acórdãos indexados.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        termo = st.text_input("🔍 Buscar termo exato", "")
    with col2:
        relatores = sorted(df['relator'].replace('', pd.NA).dropna().unique().tolist())
        relator = st.selectbox("👤 Filtrar por Relator", ["Todos"] + relatores)
    with col3:
        if 'ano' in df.columns:
            anos = sorted(df['ano'].replace('', pd.NA).dropna().unique().tolist())
        else:
            anos = []
        ano = st.selectbox("📅 Filtrar por Ano", ["Todos"] + anos)
        
    df_filtrado = df.copy()
    
    if termo:
        df_filtrado = df_filtrado[df_filtrado.apply(lambda row: row.astype(str).str.contains(termo, case=False).any(), axis=1)]
    if relator != "Todos":
        df_filtrado = df_filtrado[df_filtrado['relator'] == relator]
    if ano != "Todos":
        df_filtrado = df_filtrado[df_filtrado['ano'] == ano]
        
    st.write(f"Mostrando **{len(df_filtrado)}** resultados relevantes.")
    st.dataframe(df_filtrado, use_container_width=True)
    
    st.divider()
    st.subheader("📈 Estatísticas Rápidas")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Top 10 Relatores**")
        st.bar_chart(df_filtrado['relator'].replace('', pd.NA).dropna().value_counts().head(10))
    with c2:
        if 'ano' in df_filtrado.columns:
            st.write("**Acórdãos por Ano**")
            st.line_chart(df_filtrado['ano'].replace('', pd.NA).dropna().value_counts().sort_index())

else:
    st.warning("Nenhuma base vetorial indexada encontrada. Certifique-se de que o Motor RAG foi inicializado e/ou o Firebase está configurado.")
