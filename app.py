import streamlit as st
import anthropic
import google.generativeai as genai
from openai import OpenAI

from motor_rag import MotorRAG

with st.sidebar:
    st.title("🏛️ TCU Search")
    st.caption("Pesquisa Inteligente de Acórdãos")
    
    provedor = st.selectbox(
        "Provedor de IA",
        ["OpenAI (ChatGPT)", "Anthropic (Claude)", "Google (Gemini)"],
        index=0
    )

    api_key_placeholder = "sk-..." if "OpenAI" in provedor or "Anthropic" in provedor else "AIzaSy..."
    api_key_name = f"{provedor.split(' ')[0]} API Key"

    llm_api_key = st.text_input(
        api_key_name,
        type="password",
        key=f"api_key_{provedor}",
        placeholder=api_key_placeholder,
    )
    
    if "OpenAI" in provedor:
        modelos = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
    elif "Anthropic" in provedor:
        modelos = ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
    else:
        modelos = ["gemini-1.5-flash", "gemini-1.5-pro"]

    modelo_llm = st.selectbox("Modelo", modelos, index=0)
    top_k = st.slider("Resultados por busca", 1, 15, 5)
    
    if st.button("Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("💬 Chatbot TCU")
st.caption("🚀 Uma pesquisa de acórdãos TCU alimentada por IA e RAG local")

@st.cache_resource
def inicializar_rag():
    try:
        motor = MotorRAG()
        motor.inicializar()
        return motor
    except FileNotFoundError as e:
        return None
    except Exception as e:
        st.error(f"Erro ao inicializar RAG: {e}")
        return None

motor = inicializar_rag()

if not motor:
    st.error("RAG não inicializado. Verifique se os arquivos `.csv` estão na pasta `data/`.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Como posso ajudar você com a jurisprudência do TCU hoje?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    if not llm_api_key:
        st.info(f"Please add your {provedor.split(' ')[0]} API key to continue.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        # Buscar acórdãos (RAG)
        contexto = ""
        resultados = motor.buscar(prompt, top_k=top_k)
        if resultados:
            contexto = motor.montar_contexto(resultados)
            with st.expander(f"📚 Ver {len(resultados)} acórdão(s) base recuperados"):
                for doc in resultados:
                    meta = doc["metadados"]
                    st.markdown(f"**Acórdão {meta.get('num_acordao', '?')}/{meta.get('ano', '?')}**")
                    st.markdown(f"*Relator: {meta.get('relator', 'N/A')}* | *Assunto: {meta.get('assunto', 'N/A')}*")
                    st.text(meta.get('sumario', 'Sem sumário')[:200] + "...")
                    st.divider()

        # Preparar chamadas do LLM    
        SYSTEM_PROMPT = "Você é um assistente configurado para analisar acórdãos do TCU. Responda baseado prioritariamente no contexto fornecido. Se não houver contexto, seja claro quanto a isso. Responda em português."
        
        # Histórico sem a msg inicial padrão se houver, ou apenas formatado
        mensagens_historico = []
        for m in st.session_state.messages[-7:]:
            # Ignorar a primeira de saudação se não ajudar
            if m["content"].startswith("Como posso"): continue
            mensagens_historico.append({"role": m["role"], "content": m["content"]})
            
        resposta = ""
        try:
            if "OpenAI" in provedor:
                client = OpenAI(api_key=llm_api_key)
                msgs = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "system", "content": f"CONTEXTO DOS ACÓRDÃOS:\n{contexto}"}
                ] + mensagens_historico
                
                response = client.chat.completions.create(model=modelo_llm, messages=msgs, temperature=0.3)
                resposta = response.choices[0].message.content

            elif "Anthropic" in provedor:
                client = anthropic.Anthropic(api_key=llm_api_key)
                sys_msg = f"{SYSTEM_PROMPT}\n\nCONTEXTO:\n{contexto}"
                
                response = client.messages.create(
                    model=modelo_llm,
                    system=sys_msg,
                    messages=mensagens_historico,
                    max_tokens=2000,
                    temperature=0.3
                )
                resposta = response.content[0].text

            else:
                genai.configure(api_key=llm_api_key)
                sys_msg = f"{SYSTEM_PROMPT}\n\nCONTEXTO:\n{contexto}"
                model = genai.GenerativeModel(model_name=modelo_llm, system_instruction=sys_msg)
                
                hist = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in mensagens_historico[:-1]]
                chat = model.start_chat(history=hist)
                response = chat.send_message(prompt, generation_config=genai.types.GenerationConfig(temperature=0.3))
                resposta = response.text

            st.write(resposta)
            st.session_state.messages.append({"role": "assistant", "content": resposta})
            
        except Exception as e:
            st.error(f"Erro ao gerar resposta ({provedor.split(' ')[0]}): {e}")
