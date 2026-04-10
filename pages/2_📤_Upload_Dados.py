"""
📤 Upload de Dados
Página para upload de arquivos CSV com acórdãos do TCU.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import shutil

st.set_page_config(
    page_title="Upload de Dados | TCU Search",
    page_icon="📤",
    layout="wide",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .upload-zone {
        background: linear-gradient(145deg, #1A1F2B 0%, #1f2535 100%);
        border: 2px dashed rgba(27, 107, 147, 0.4);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }

    .upload-zone:hover {
        border-color: #1B6B93;
        background: linear-gradient(145deg, #1f2535 0%, #252b3b 100%);
    }

    .format-card {
        background: rgba(27, 107, 147, 0.1);
        border: 1px solid rgba(27, 107, 147, 0.2);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📤 Upload de Dados")
st.caption("Carregue arquivos CSV com acórdãos do TCU")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Instruções
st.markdown(
    """
<div class="upload-zone">
    <h3 style="color: #4ecdc4; margin-bottom: 0.5rem">📁 Arraste seus arquivos CSV aqui</h3>
    <p style="color: rgba(255,255,255,0.5); font-size: 0.9rem;">
        Aceitamos arquivos CSV com dados de acórdãos do TCU
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# Upload
uploaded_files = st.file_uploader(
    "Selecione arquivos CSV",
    type=["csv"],
    accept_multiple_files=True,
    key="csv_uploader",
    label_visibility="collapsed",
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Ler para validar
            df = pd.read_csv(uploaded_file, encoding="utf-8", dtype=str, nrows=5)

            st.success(f"✅ **{uploaded_file.name}** — {len(df.columns)} colunas detectadas")

            # Preview
            with st.expander(f"👁️ Preview de {uploaded_file.name}"):
                st.dataframe(df, use_container_width=True)

            # Salvar
            destino = DATA_DIR / uploaded_file.name
            uploaded_file.seek(0)
            with open(destino, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.info(f"💾 Salvo em `{destino}`")

        except Exception as e:
            st.error(f"❌ Erro ao processar {uploaded_file.name}: {e}")

    st.markdown("---")
    st.warning(
        "⚠️ **Após o upload**, clique em **🔄 Reindexar base** na barra lateral "
        "da página principal para atualizar o índice de busca."
    )

st.markdown("---")

# Formato esperado
st.markdown("##### 📋 Formato Esperado do CSV")

st.markdown(
    """
<div class="format-card">
    <strong>Colunas principais:</strong><br>
    <code>numAcordao</code>, <code>anoAcordao</code>, <code>colegiado</code>,
    <code>relator</code>, <code>tipoProcesso</code>, <code>assunto</code>,
    <code>sumario</code>, <code>acordao</code>, <code>entidade</code>,
    <code>dtSessao</code>, <code>numProc</code>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
> 💡 **Dica:** Use o script `coletar_acordaos.py` para gerar automaticamente
> um CSV com o formato correto a partir da API do TCU:
>
> ```bash
> python coletar_acordaos.py --quantidade 1000 --output data/acordaos.csv
> ```
"""
)

# Arquivos existentes
st.markdown("---")
st.markdown("##### 📂 Arquivos na pasta `data/`")

csvs_existentes = list(DATA_DIR.glob("*.csv"))
if csvs_existentes:
    for csv_file in csvs_existentes:
        tamanho = csv_file.stat().st_size
        tamanho_str = (
            f"{tamanho / 1024:.1f} KB"
            if tamanho < 1024 * 1024
            else f"{tamanho / (1024 * 1024):.1f} MB"
        )

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"📄 **{csv_file.name}**")
        with col2:
            st.markdown(f"`{tamanho_str}`")
        with col3:
            if st.button("🗑️", key=f"del_{csv_file.name}", help=f"Remover {csv_file.name}"):
                csv_file.unlink()
                st.rerun()
else:
    st.info("Nenhum arquivo CSV encontrado na pasta `data/`.")
