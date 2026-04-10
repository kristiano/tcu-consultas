"""
🏛️ Pesquisa Inteligente de Acórdãos do TCU
Aplicação Streamlit com RAG (Retrieval-Augmented Generation)

Interface inspirada em https://github.com/streamlit/llm-examples
Dados baseados na estratégia de https://github.com/netoferraz/acordaos-tcu
"""

import streamlit as st
import anthropic
import google.generativeai as genai
from openai import OpenAI

from motor_rag import MotorRAG

# ─── Configuração da Página ──────────────────────────────────────────────────

st.set_page_config(
    page_title="Pesquisa TCU | Acórdãos com IA",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS Customizado Premium ─────────────────────────────────────────────────

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Reset e tipografia global */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Header animado */
    .main-header {
        background: linear-gradient(135deg, #0a1628 0%, #1B6B93 50%, #27496d 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(27, 107, 147, 0.3);
        box-shadow: 0 8px 32px rgba(27, 107, 147, 0.15);
    }

    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(
            circle at 30% 50%,
            rgba(78, 205, 196, 0.08) 0%,
            transparent 50%
        );
        animation: shimmer 8s ease-in-out infinite;
    }

    @keyframes shimmer {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(5%, 5%); }
    }

    .main-header h1 {
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 0.5rem 0;
        position: relative;
        z-index: 1;
    }

    .main-header p {
        font-size: 0.95rem;
        color: rgba(255, 255, 255, 0.75);
        margin: 0;
        position: relative;
        z-index: 1;
    }

    /* Cards de estatísticas */
    .stat-card {
        background: linear-gradient(145deg, #1A1F2B 0%, #252b3b 100%);
        border: 1px solid rgba(27, 107, 147, 0.25);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        border-color: rgba(27, 107, 147, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(27, 107, 147, 0.15);
    }

    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #4ecdc4;
        line-height: 1;
    }

    .stat-label {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.4rem;
    }

    /* Resultados de busca */
    .acordao-card {
        background: linear-gradient(145deg, #1A1F2B 0%, #1f2535 100%);
        border: 1px solid rgba(27, 107, 147, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .acordao-card:hover {
        border-color: #1B6B93;
        box-shadow: 0 4px 24px rgba(27, 107, 147, 0.1);
    }

    .acordao-titulo {
        font-size: 1.1rem;
        font-weight: 600;
        color: #4ecdc4;
        margin-bottom: 0.75rem;
    }

    .acordao-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .meta-badge {
        background: rgba(27, 107, 147, 0.15);
        border: 1px solid rgba(27, 107, 147, 0.3);
        border-radius: 8px;
        padding: 0.3rem 0.75rem;
        font-size: 0.78rem;
        color: rgba(255, 255, 255, 0.8);
    }

    .acordao-sumario {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.7);
        line-height: 1.6;
        border-left: 3px solid #1B6B93;
        padding-left: 1rem;
        margin-top: 0.75rem;
    }

    /* Chat messages */
    .stChatMessage {
        border-radius: 12px !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E1117 0%, #151922 100%);
    }

    section[data-testid="stSidebar"] .stMarkdown a {
        color: #4ecdc4;
        text-decoration: none;
    }

    section[data-testid="stSidebar"] .stMarkdown a:hover {
        color: #7eddd6;
        text-decoration: underline;
    }

    /* Status indicator */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }

    .status-online { background: #4ecdc4; }
    .status-offline { background: #e74c3c; }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, #1B6B93 0%, #27496d 100%);
        border: 1px solid rgba(27, 107, 147, 0.5);
        border-radius: 10px;
        color: white;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #2580ab 0%, #326185 100%);
        border-color: #1B6B93;
        box-shadow: 0 4px 16px rgba(27, 107, 147, 0.25);
        transform: translateY(-1px);
    }

    /* Spinner overlay */
    .loading-overlay {
        text-align: center;
        padding: 2rem;
        color: rgba(255, 255, 255, 0.6);
    }

    /* Divider */
    .custom-divider {
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(27, 107, 147, 0.3), transparent);
        margin: 1.5rem 0;
    }

    /* Footer */
    .footer-info {
        text-align: center;
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.3);
        padding: 1rem 0;
    }

    /* Esconder âncoras de header */
    .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {
        display: none !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ─── Prompt do Sistema ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é um assistente jurídico especializado em jurisprudência do Tribunal de Contas da União (TCU).

Sua função é ajudar o usuário a pesquisar e compreender acórdãos do TCU.

REGRAS:
1. Responda SEMPRE em português brasileiro.
2. Base suas respostas EXCLUSIVAMENTE nos acórdãos fornecidos no contexto.
3. Cite os números dos acórdãos quando referenciar decisões específicas.
4. Se o contexto não contiver informações suficientes, informe ao usuário.
5. Organize suas respostas de forma clara com tópicos e destaques.
6. Quando relevante, mencione o relator, a entidade e o colegiado.
7. Use linguagem técnic-jurídica quando apropriado, mas explique termos complexos.

FORMATO DE RESPOSTA:
- Use emojis moderadamente para melhor legibilidade
- Estruture com bullets e sub-tópicos
- Destaque números de acórdãos em **negrito**
- Inclua links para download quando disponíveis nos metadados
"""


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
    <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
        <span style="font-size: 2rem;">🏛️</span>
        <h3 style="margin: 0.25rem 0 0 0; font-weight: 700; color: #4ecdc4;">
            TCU Search
        </h3>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin: 0;">
            Pesquisa Inteligente de Acórdãos
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Input da API Key
    provedor = st.selectbox(
        "🧠 Provedor de IA",
        ["OpenAI (ChatGPT)", "Anthropic (Claude)", "Google (Gemini)"],
        index=0
    )

    api_key_placeholder = "sk-..." if "OpenAI" in provedor or "Anthropic" in provedor else "AIzaSy..."
    api_key_name = f"Chave da API ({provedor.split(' ')[0]})"

    llm_api_key = st.text_input(
        f"🔑 {api_key_name}",
        type="password",
        key=f"api_key_{provedor}",
        placeholder=api_key_placeholder,
        help="Necessária para gerar as respostas da IA",
    )

    if llm_api_key:
        st.markdown(
            '<span class="status-dot status-online"></span> API Key configurada',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-dot status-offline"></span> API Key não configurada',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Configurações
    st.markdown("##### ⚙️ Configurações")

    if "OpenAI" in provedor:
        modelos = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
    elif "Anthropic" in provedor:
        modelos = ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
    else:
        modelos = ["gemini-1.5-flash", "gemini-1.5-pro"]

    modelo_llm = st.selectbox(
        "Modelo LLM",
        modelos,
        index=0,
        help="Modelo usado para gerar repostas baseadas nos acórdãos",
    )

    top_k = st.slider(
        "Resultados por busca",
        min_value=1,
        max_value=15,
        value=5,
        help="Quantidade de acórdãos recuperados para contexto",
    )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Links úteis
    st.markdown("##### 🔗 Links Úteis")
    st.markdown(
        """
    - [Portal TCU](https://portal.tcu.gov.br/)
    - [Jurisprudência TCU](https://pesquisa.apps.tcu.gov.br/)
    - [Obter API Key OpenAI](https://platform.openai.com/api-keys)
    """
    )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Ações
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🔄 Reindexar base", use_container_width=True):
        if "motor_rag" in st.session_state:
            del st.session_state["motor_rag"]
        if "indexado" in st.session_state:
            del st.session_state["indexado"]
        st.rerun()


# ─── Header Principal ────────────────────────────────────────────────────────

st.markdown(
    """
<div class="main-header">
    <h1>🏛️ Pesquisa Inteligente de Acórdãos do TCU</h1>
    <p>Busca semântica com IA sobre a base de acórdãos do Tribunal de Contas da União.
    Pergunte sobre licitações, contratos, prestação de contas, e muito mais.</p>
</div>
""",
    unsafe_allow_html=True,
)


# ─── Inicialização do Motor RAG ──────────────────────────────────────────────


def inicializar_rag():
    """Inicializa o motor RAG e indexa os documentos localmente."""
    if "motor_rag" not in st.session_state or "indexado" not in st.session_state:
        try:
            motor = MotorRAG()
            num_docs = motor.inicializar()
            st.session_state["motor_rag"] = motor
            st.session_state["indexado"] = True
            st.session_state["num_docs"] = num_docs
            st.session_state["stats"] = motor.estatisticas()
            return motor
        except FileNotFoundError as e:
            st.error(f"📁 {e}")
            st.info(
                "**Para começar:**\n"
                "1. Execute `python coletar_acordaos.py` para baixar acórdãos\n"
                "2. Ou coloque seus arquivos `.csv` na pasta `data/`"
            )
            return None
        except Exception as e:
            st.error(f"❌ Erro ao inicializar: {e}")
            return None
    else:
        return st.session_state["motor_rag"]


# ─── Exibir estatísticas da base ──────────────────────────────────────────────

with st.spinner("🔄 Indexando base de acórdãos com embeddings locais..."):
    motor = inicializar_rag()

    if motor and "stats" in st.session_state:
        stats = st.session_state["stats"]
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-number">{stats.get('total', 0):,}</div>
                <div class="stat-label">Acórdãos Indexados</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with col2:
            anos = stats.get("anos", [])
            periodo = f"{anos[0]}–{anos[-1]}" if len(anos) >= 2 else (anos[0] if anos else "–")
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-number" style="font-size:1.4rem">{periodo}</div>
                <div class="stat-label">Período</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-number">{len(stats.get('colegiados', []))}</div>
                <div class="stat-label">Colegiados</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f"""
            <div class="stat-card">
                <div class="stat-number">{stats.get('total_relatores', 0)}</div>
                <div class="stat-label">Relatores</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# ─── Sugestões de Perguntas ──────────────────────────────────────────────────

if motor and "motor_rag" in st.session_state:
    if "messages" not in st.session_state or len(st.session_state.messages) == 0:
        st.markdown("##### 💡 Sugestões de pesquisa")
        sugestoes = [
            "Quais acórdãos tratam de dispensa de licitação indevida?",
            "Encontre decisões sobre irregularidades em contratos administrativos",
            "Quais são os entendimentos do TCU sobre pregão eletrônico?",
            "Mostre acórdãos relacionados a prestação de contas e tomada de contas especial",
        ]

        cols = st.columns(2)
        for i, sugestao in enumerate(sugestoes):
            with cols[i % 2]:
                if st.button(f"🔍 {sugestao}", key=f"sug_{i}", use_container_width=True):
                    st.session_state["sugestao_selecionada"] = sugestao
                    st.rerun()


# ─── Histórico de Mensagens ──────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🏛️"):
        st.markdown(msg["content"])

# ─── Input do Chat ───────────────────────────────────────────────────────────

# Verificar se há sugestão selecionada
prompt = None
if "sugestao_selecionada" in st.session_state:
    prompt = st.session_state.pop("sugestao_selecionada")

if prompt is None:
    prompt = st.chat_input(
        "Pesquise acórdãos do TCU... Ex: 'decisões sobre superfaturamento em obras públicas'"
    )

if prompt:
    if not llm_api_key:
        st.info("🔑 Por favor, insira a sua API Key do provedor selecionado na barra lateral para conversar.")
        st.stop()

    if "motor_rag" not in st.session_state:
        st.error("❌ Motor RAG não inicializado. Verifique os dados na pasta `data/`.")
        st.stop()

    motor = st.session_state["motor_rag"]

    # Adicionar mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(prompt)

    # Buscar e responder
    with st.chat_message("assistant", avatar="🏛️"):
        with st.spinner("🔎 Buscando acórdãos relevantes..."):
            try:
                resultados = motor.buscar(prompt, top_k=top_k)
                contexto = motor.montar_contexto(resultados)
            except Exception as e:
                st.error(f"Erro na busca: {e}")
                st.stop()

        # Mostrar os acórdãos encontrados em expander
        if resultados:
            with st.expander(f"📚 {len(resultados)} acórdão(s) encontrado(s)", expanded=False):
                for i, doc in enumerate(resultados, 1):
                    meta = doc["metadados"]
                    titulo = meta.get('titulo', f"Acórdão {meta.get('num_acordao', '?')}/{meta.get('ano', '?')}")
                    relator = meta.get("relator", "")
                    assunto = meta.get("assunto", "")

                    st.markdown(
                        f"""
                    <div class="acordao-card">
                        <div class="acordao-titulo">📋 {titulo}</div>
                        <div class="acordao-meta">
                            <span class="meta-badge">👤 {relator}</span>
                            <span class="meta-badge">📅 {meta.get('data_sessao', 'N/A')}</span>
                        </div>
                        <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">
                            <strong>Assunto:</strong> {assunto}
                        </div>
                        <div class="acordao-sumario">
                            {meta.get('sumario', 'Sumário não disponível')[:300]}...
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

        # Gerar resposta do LLM com contexto RAG
        with st.spinner(f"🤖 Gerando análise via {provedor.split(' ')[0]}..."):
            
            # Preparar o histórico de mensagens e contexto base
            mensagens_historico = []
            for msg in st.session_state.messages[-6:]:
               mensagens_historico.append({"role": msg["role"], "content": msg["content"]})
               
            try:
                if "OpenAI" in provedor:
                    client = OpenAI(api_key=llm_api_key)
                    mensagens_llm = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "system", "content": f"CONTEXTO DOS ACÓRDÃOS RECUPERADOS:\n{contexto}"},
                    ] + mensagens_historico
                    
                    response = client.chat.completions.create(
                        model=modelo_llm,
                        messages=mensagens_llm,
                        temperature=0.3,
                        max_tokens=2000,
                    )
                    resposta = response.choices[0].message.content
                    
                elif "Anthropic" in provedor:
                    client = anthropic.Anthropic(api_key=llm_api_key)
                    system_message = f"{SYSTEM_PROMPT}\n\nCONTEXTO DOS ACÓRDÃOS RECUPERADOS:\n{contexto}"
                    
                    # Anthropic expecta mensagens user/assistant alternadas
                    response = client.messages.create(
                        model=modelo_llm,
                        max_tokens=2000,
                        system=system_message,
                        messages=mensagens_historico,
                        temperature=0.3,
                    )
                    resposta = response.content[0].text
                    
                else:  # Google Gemini
                    genai.configure(api_key=llm_api_key)
                    system_message = f"{SYSTEM_PROMPT}\n\nCONTEXTO DOS ACÓRDÃOS RECUPERADOS:\n{contexto}"
                    model = genai.GenerativeModel(
                        model_name=modelo_llm,
                        system_instruction=system_message
                    )
                    
                    # O formato de mensagens do Gemini é um pouco diferente ({role: "user"/"model", parts: [...]})
                    gemini_history = []
                    for msg in mensagens_historico[:-1]:  # Excluir a última pro chat normal
                        gemini_role = "user" if msg["role"] == "user" else "model"
                        gemini_history.append({"role": gemini_role, "parts": [msg["content"]]})
                    
                    chat = model.start_chat(history=gemini_history)
                    ultimo_prompt = mensagens_historico[-1]["content"] if mensagens_historico else ""
                    response = chat.send_message(ultimo_prompt, generation_config=genai.types.GenerationConfig(temperature=0.3))
                    resposta = response.text
                    
            except Exception as e:
                resposta = f"❌ Erro ao gerar resposta ({provedor.split(' ')[0]}): {e}"

        st.markdown(resposta)

    # Salvar resposta
    st.session_state.messages.append({"role": "assistant", "content": resposta})


# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="footer-info">
    <hr class="custom-divider">
    Pesquisa Inteligente de Acórdãos do TCU • RAG + OpenAI •
    Dados: <a href="https://dados-abertos.apps.tcu.gov.br/" target="_blank" style="color: rgba(255,255,255,0.4);">API Dados Abertos TCU</a>
</div>
""",
    unsafe_allow_html=True,
)
