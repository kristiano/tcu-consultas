# TCU Search - Pesquisa Inteligente de Acórdãos 🏛️

Uma aplicação de **Pesquisa Semântica Avançada** utilizando uma arquitetura inovadora de **Vectorless RAG (Agentic RAG)** focada nos acórdãos do Tribunal de Contas da União (TCU). 

Construído com [Streamlit](https://streamlit.io/), o aplicativo aposenta modelos vetoriais tradicionais pesados e de baixa precisão (como FAISS) para aplicar Raciocínio de Inteligência Artificial Puro usando LLMs para vasculhar e pinçar textos massivos na íntegra.

---

## ✨ A Nova Arquitetura Híbrida: Vectorless RAG

Em vez de picotar os processos em vetores matemáticos ("Chunking") e perder o raciocínio completo do ministro relator, nós implementamos um conceito de Raciocínio Mapeado:

1. **Catálogo Python (Custo Zero):** Um robô em Python puro lê a sua base de CSV bruta gigantesca e constrói um índice sumário (`catalogo_acordaos.json`) levíssimo, de graça.
2. **A IA como Rastreadora:** Na hora da pergunta, inserimos toda essa árvore de sumários no LLM (aproveitando as janelas gigantes do Gemini). A IA decide, baseada apenas no sumário, quais Acórdãos ela quer ler ativamente.
3. **Pescando a Íntegra:** O Python intercepta as escolhas da IA, mergulha no arquivo `CSV` central, e puxa **100% da íntegra** dos Acórdãos escolhidos, devolvendo tudo ao LLM para que ele consiga dar a resposta impecável sem perda de contexto judicial.

### Funcionalidades
*   **🤖 Cloud LLM Tracking:** Por conta do limite de contexto para leitura de Catálogos maciços, nosso indexador base utiliza a engine do **Google (Gemini 2.5 Flash / Pro)** como navegador da árvore de decisões.
*   **📡 Integração Firebase Storage Integrada:** Arquivos de processos do TCU possuem centenas de Megabytes. Como o GitHub bloqueia arquivos `>100MB`, incluímos integração automática com o Firebase. O seu Streamlit na Web baixa a base automaticamente do Firebase Storage de forma invisível.

---

## 🛠️ Instalação e Uso Local

### 1. Clonar e preparar o ambiente
```bash
git clone https://github.com/SEU-USUARIO/app-tcu1.git
cd app-tcu1
```

### 2. Instalar dependências
(É altamente recomendado usar ambiente virtual: `python -m venv venv` e `source venv/bin/activate`)
```bash
pip install -r requirements.txt
```

### 3. Preparação das Bases de Dados
Você precisa do CSV original que será lido pela aplicação. 
Coloque o seu arquivo `.csv` do TCU na raiz com o nome **`acordao-completo-2026.csv`**.

Rode o nosso Indexador Local offline para que ele crie o mapa lógico JSON automaticamente:
```bash
python indexador_offline.py
```
> Isso irá gerar automaticamente o `catalogo_acordaos.json`.

### 4. Executar o aplicativo Streamlit
```bash
streamlit run app.py
```
Abra o navegador e cole a sua `API Key` do Google Gemini na barra lateral para usufruir da busca.

---

## ☁️ Deploy para Produção (Streamlit Community Cloud)

Ao submeter seu código para o GitHub, **não mande o arquivo CSV ou JSON de dados**. Seu `.gitignore` já está configurado para bloquear.

1. Suba este código para o seu Github.
2. Acesse seu painel do Firebase, vá em **Storage** e arraste os seus dois arquivos (`acordao-completo-2026.csv` e `catalogo_acordaos.json`) para a raiz.
3. Entre no seu Streamlit Cloud e em configurações (*Advanced Settings > Secrets*), configure suas chaves do Firebase:
```toml
[firebase]
type = "service_account"
project_id = "tcu-app-..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```
O App iniciará, se conectará de forma invisível no Storage, e fará o download local automático!

---

## 🤝 Créditos
Inspirado pelos projetos de referência:
1. Trabalhos originais [Base de Acórdãos TCU (Neto Ferraz)](https://github.com/netoferraz/acordaos-tcu)
2. Arquiteturas de Raciocínio Vetorial [PageIndex da VectifyAI](https://github.com/VectifyAI/PageIndex)

Nenhuma das bases utilizadas têm caráter oficial imediato extraída sob garantias. É prudente comparar as decisões localizadas pela IA diretamente no [Portal Oficial do TCU](https://pesquisa.apps.tcu.gov.br/).
