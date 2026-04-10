"""
📊 Explorar Base de Acórdãos
Página para visualizar e filtrar a base de dados carregada.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Explorar Base | TCU Search",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stat-mini {
        background: linear-gradient(145deg, #1A1F2B 0%, #252b3b 100%);
        border: 1px solid rgba(27, 107, 147, 0.2);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stat-mini-num {
        font-size: 1.5rem;
        font-weight: 700;
        color: #4ecdc4;
    }
    .stat-mini-label {
        font-size: 0.72rem;
        color: rgba(255,255,255,0.45);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📊 Explorar Base de Acórdãos")
st.caption("Visualize, filtre e navegue pelos acórdãos carregados")

DATA_DIR = Path("data")


@st.cache_data
def carregar_dados():
    """Carrega todos os CSVs do diretório data/."""
    if not DATA_DIR.exists():
        return None

    csvs = list(DATA_DIR.glob("*.csv"))
    if not csvs:
        return None

    dfs = []
    for f in csvs:
        try:
            df = pd.read_csv(f, encoding="utf-8", dtype=str).fillna("")
            dfs.append(df)
        except Exception:
            pass

    if not dfs:
        return None

    return pd.concat(dfs, ignore_index=True)


df = carregar_dados()

if df is None or df.empty:
    st.warning(
        "📁 Nenhum dado encontrado. Execute o coletor primeiro:\n\n"
        "```bash\npython coletar_acordaos.py --quantidade 500\n```"
    )
    st.stop()

# Estatísticas rápidas
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(
        f'<div class="stat-mini"><div class="stat-mini-num">{len(df):,}</div>'
        f'<div class="stat-mini-label">Total</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    anos = df["anoAcordao"].unique() if "anoAcordao" in df.columns else []
    st.markdown(
        f'<div class="stat-mini"><div class="stat-mini-num">{len(anos)}</div>'
        f'<div class="stat-mini-label">Anos</div></div>',
        unsafe_allow_html=True,
    )
with col3:
    colegiados = df["colegiado"].unique() if "colegiado" in df.columns else []
    st.markdown(
        f'<div class="stat-mini"><div class="stat-mini-num">{len(colegiados)}</div>'
        f'<div class="stat-mini-label">Colegiados</div></div>',
        unsafe_allow_html=True,
    )
with col4:
    relatores = df["relator"].nunique() if "relator" in df.columns else 0
    st.markdown(
        f'<div class="stat-mini"><div class="stat-mini-num">{relatores}</div>'
        f'<div class="stat-mini-label">Relatores</div></div>',
        unsafe_allow_html=True,
    )
with col5:
    entidades = df["entidade"].nunique() if "entidade" in df.columns else 0
    st.markdown(
        f'<div class="stat-mini"><div class="stat-mini-num">{entidades}</div>'
        f'<div class="stat-mini-label">Entidades</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# Filtros
st.markdown("##### 🔍 Filtros")
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    filtro_ano = st.multiselect(
        "Ano",
        sorted(df["anoAcordao"].unique()) if "anoAcordao" in df.columns else [],
    )

with col_f2:
    filtro_colegiado = st.multiselect(
        "Colegiado",
        sorted(df["colegiado"].unique()) if "colegiado" in df.columns else [],
    )

with col_f3:
    filtro_texto = st.text_input("Busca por texto (sumário/assunto)", "")

# Aplicar filtros
df_filtrado = df.copy()
if filtro_ano:
    df_filtrado = df_filtrado[df_filtrado["anoAcordao"].isin(filtro_ano)]
if filtro_colegiado:
    df_filtrado = df_filtrado[df_filtrado["colegiado"].isin(filtro_colegiado)]
if filtro_texto:
    mask = (
        df_filtrado.get("sumario", pd.Series(dtype=str))
        .str.contains(filtro_texto, case=False, na=False)
    ) | (
        df_filtrado.get("assunto", pd.Series(dtype=str))
        .str.contains(filtro_texto, case=False, na=False)
    )
    df_filtrado = df_filtrado[mask]

st.markdown(f"**{len(df_filtrado):,}** acórdãos encontrados")

# Colunas para exibição
colunas_exibir = [
    "numAcordao",
    "anoAcordao",
    "colegiado",
    "relator",
    "tipoProcesso",
    "assunto",
    "dtSessao",
]
colunas_disponiveis = [c for c in colunas_exibir if c in df_filtrado.columns]

st.dataframe(
    df_filtrado[colunas_disponiveis].head(200),
    use_container_width=True,
    height=500,
    column_config={
        "numAcordao": st.column_config.TextColumn("Nº Acórdão"),
        "anoAcordao": st.column_config.TextColumn("Ano"),
        "colegiado": st.column_config.TextColumn("Colegiado"),
        "relator": st.column_config.TextColumn("Relator"),
        "tipoProcesso": st.column_config.TextColumn("Tipo"),
        "assunto": st.column_config.TextColumn("Assunto", width="large"),
        "dtSessao": st.column_config.TextColumn("Data Sessão"),
    },
)

# Detalhes de um acórdão selecionado
st.markdown("---")
st.markdown("##### 📋 Detalhes do Acórdão")

if not df_filtrado.empty:
    opcoes = [
        f"Acórdão {row.get('numAcordao', '?')}/{row.get('anoAcordao', '?')} - {row.get('colegiado', '')}"
        for _, row in df_filtrado.head(50).iterrows()
    ]
    selecao = st.selectbox("Selecione um acórdão:", opcoes)

    if selecao:
        idx = opcoes.index(selecao)
        row = df_filtrado.iloc[idx]

        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**Número:** {row.get('numAcordao', 'N/A')}")
            st.markdown(f"**Ano:** {row.get('anoAcordao', 'N/A')}")
            st.markdown(f"**Colegiado:** {row.get('colegiado', 'N/A')}")
            st.markdown(f"**Relator:** {row.get('relator', 'N/A')}")
            st.markdown(f"**Processo:** {row.get('numProc', 'N/A')}")
            st.markdown(f"**Tipo:** {row.get('tipoProcesso', 'N/A')}")
            st.markdown(f"**Data:** {row.get('dtSessao', 'N/A')}")
            st.markdown(f"**Entidade:** {row.get('entidade', 'N/A')}")

        with c2:
            st.markdown("**📝 Assunto:**")
            st.info(row.get("assunto", "Não disponível"))
            st.markdown("**📄 Sumário:**")
            st.text_area(
                "Sumário",
                row.get("sumario", "Não disponível"),
                height=200,
                label_visibility="collapsed",
            )
