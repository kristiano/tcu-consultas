# TCU Search - Pesquisa Inteligente de Acórdãos 🏛️

Uma aplicação de **Pesquisa Semântica** e **RAG** (Retrieval-Augmented Generation) focada nos acórdãos do Tribunal de Contas da União (TCU). 

Este aplicativo foi construído com a biblioteca [Streamlit](https://streamlit.io/) e desenhado para permitir aos usuários realizar perguntas complexas baseadas na jurisprudência do TCU. Ele utiliza embeddings para ler, entender e entregar respostas analíticas usando o seu provedor de Inteligência Artificial favorito!

## ✨ Funcionalidades
*   **🤖 Multi-Provedor de IAs:** Você pode escolher qual LLM irá responder as perguntas:
    *   **OpenAI** (Modelos GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo)
    *   **Anthropic** (Modelos Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku)
    *   **Google Gemini** (Modelos 1.5 Flash e 1.5 Pro)
*   **🔍 Indexação 100% Local e Gratuita:** A fase de embeddings (vetorização dos textos longos) é feita utilizando modelos `sentence-transformers` direto na sua máquina CPU/GPU usando FAISS. Isso significa que **não há custos de tokens** para indexar a base de dados.
*   **📊 Explorador de Dados:** Uma interface separada voltada puramente para analisar métricas, tabelas estatísticas, ler os acórdãos inteiros e filtrar tudo (páginas laterais).
*   **📥 Coletor e Upload:** Possui tanto scripts de terminal automáticos para baixar novos acórdãos direto da API Pública do TCU, ou opções flexíveis para você fazer o drag-and-drop dos seus arquivos `.csv`.

---

## 🛠️ Instalação e Uso

### 1. Clonar e preparar o ambiente
```bash
git clone https://github.com/SEU-USUARIO/app-tcu1.git
cd app-tcu1
```

### 2. Instalar dependências
(É recomendado criar um ambiente virtual antes `python -m venv venv`)
```bash
pip install -r requirements.txt
```

### 3. Base de Dados (CSVs)
O aplicativo espera que seus dados estejam na pasta **`data/`**.
Temos três opções para você obter os dados:
1. **Através do Coletor (API TCU):** 
   Rode no terminal para extrair 500 acórdãos oficiais na hora: 
   `python coletar_acordaos.py --quantidade 500`
2. **Kaggle Dataset / Seus arquivos locais:**
   Coloque o arquivo `total-tcu.csv` (ou qualquer outro com as mesmas colunas) diretamente na subpasta `data/`.
3. **Upload Visual:**
   Inicie o aplicativo e acesse a página "📤 Upload de Dados" na aba lateral para largar seu arquivo na janela.

### 4. Executar o aplicativo
Após certificar-se que há pelo menos um `.csv` com dados na pasta correta, execute o Streamlit:
```bash
streamlit run app.py
```
O servidor inicializará, os embeddings (`all-MiniLM-L6-v2`) rodarão pela primeira vez na pasta `.cache` local, e a porta web se abrirá!
Cole sua *API Key* do provedor escolhido na barra lateral e comece a pesquisar.

---

## 📁 Estrutura do Projeto
- `app.py`: O código principal da interface e gerador de chat LLM.
- `motor_rag.py`: Lógica do sistema semântico, leitura de dataset e processador RAG com `FAISS`.
- `coletar_acordaos.py`: Script autônomo para baixar informações brutas da API oficial do TCU.
- `requirements.txt`: Todas as bibliotecas Python instaladas para rodar o app.
- `data/`: Onde ficam os arquivos em lote (`.csv`) com as bases analíticas.
- `pages/`: Aplicações e visualizações adicionais para explorar ou interagir com o sistema RAG Streamlit.

---

## 🤝 Créditos
Inspirado pelos projetos de referência:
1. [Base de Acórdãos TCU (Neto Ferraz)](https://github.com/netoferraz/acordaos-tcu)
2. [Streamlit LLM Examples](https://github.com/streamlit/llm-examples)

Nenhuma das bases utilizadas têm caráter oficial imediato extraída sob garantias. Em casos avançados jurídicos, é prudente comparar as decisões diretamente no [Portal Oficial do TCU](https://pesquisa.apps.tcu.gov.br/).
