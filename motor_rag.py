import os
import json
import pandas as pd
import streamlit as st
from typing import List, Dict, Any
from google import genai
import firebase_admin
from firebase_admin import credentials, storage

class ReasonerRAG:
    """Motor de RAG Vectorless usando PageIndex / Árvore lógica"""
    
    def __init__(self):
        self.catalogo_path = "catalogo_acordaos.json"
        self.csv_path = "acordao2026-limpo.csv"
        
        # Tenta baixar do firebase se não existirem
        if not os.path.exists(self.catalogo_path) or not os.path.exists(self.csv_path):
            self.baixar_do_firebase()
            
        # Tenta carregar o catálogo localmente
        if os.path.exists(self.catalogo_path):
            with open(self.catalogo_path, 'r', encoding='utf-8') as f:
                self.catalogo = json.load(f)
        else:
            self.catalogo = {}
            print("AVISO: Catálogo de RAG não encontrado localmente.")
            
    def baixar_do_firebase(self):
        print("Buscando base centralizada de arquivos do Firebase Storage...")
        try:
            try:
                app = firebase_admin.get_app()
            except ValueError:
                # Usa os secrets configurados no .streamlit/secrets.toml
                cred_dict = dict(st.secrets["firebase"])
                cred_dict["private_key"] = cred_dict["private_key"].replace('\\n', '\n')
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': 'tcu-app-426ad.appspot.com'
                })
            
            bucket = storage.bucket()
            
            for file_name in [self.catalogo_path, self.csv_path]:
                if not os.path.exists(file_name):
                    print(f"Baixando {file_name} da nuvem...")
                    blob = bucket.blob(file_name)
                    if blob.exists():
                        blob.download_to_filename(file_name)
                        print(f"{file_name} baixado com sucesso.")
                    else:
                        print(f"O arquivo {file_name} ainda não foi carregado no Firebase pelo administrador.")
        except Exception as e:
            print("Erro ao tentar conectar ao Firebase:", e)
            
    def _iniciar_cliente(self, api_key: str, modelo: str):
        if "gemini" in modelo.lower():
            return {"provider": "google", "client": genai.Client(api_key=api_key)}
        elif "gpt" in modelo.lower():
            from openai import OpenAI
            return {"provider": "openai", "client": OpenAI(api_key=api_key)}
        elif "claude" in modelo.lower():
            import anthropic
            return {"provider": "anthropic", "client": anthropic.Anthropic(api_key=api_key)}
        else:
            raise ValueError(f"Modelo desconhecido para RAG: {modelo}")

    def procurar_acordao_integra(self, lista_chaves: List[str]) -> str:
        """Puxa o texto completo (100% íntegra) dos acórdãos selecionados pelo LLM"""
        textos_completos = []
        if not os.path.exists(self.csv_path):
            return "CSV bruto não disponível para puxar a íntegra."
            
        print(f"Puxando a íntegra das chaves: {lista_chaves} via Python...")
        try:
            import csv
            df = pd.read_csv(self.csv_path, sep='|', quoting=csv.QUOTE_NONE, on_bad_lines='skip', engine='python')
            df.columns = df.columns.str.strip().str.replace('"', '').str.lower().str.replace(' ', '_').str.replace('ã', 'a').str.replace('ó', 'o')
            
            # Filtra pelos acórdãos selecionados
            for chave in lista_chaves:
                # Nosso catálogo usa `Num/Ano`
                pedacos = chave.split('/')
                num = pedacos[0]
                ano = pedacos[1] if len(pedacos) > 1 else ""
                
                if ano:
                    linha = df[(df['numacordao'].astype(str) == num) & (df['anoacordao'].astype(str) == ano)]
                else:
                    linha = df[df['numacordao'].astype(str) == num]
                    
                if not linha.empty:
                    row = linha.iloc[0]
                    texto_acordao = f"--- ACÓRDÃO {chave} ---\n"
                    texto_acordao += f"RELATOR: {str(row.get('relator', '')).replace('\"','')}\n"
                    texto_acordao += f"EMENTA: {str(row.get('sumario', '')).replace('\"','')}\n"
                    texto_acordao += f"DECISÃO COMPLETA: {str(row.get('acordao', row.get('voto', 'N/A'))).replace('\"','')}\n"
                    textos_completos.append(texto_acordao)
        except Exception as e:
            print("Erro ao extrair íntegra do CSV:", e)
            
        return "\n\n".join(textos_completos)

    def buscar(self, query: str, api_key: str, modelo_escolhido="gemini-2.5-flash", k=3) -> Dict[str, Any]:
        """Realiza a busca inteligente em 2 etapas"""
        
        # Etapa 1: Agente Árvore de Raciocínio lê o catálogo de índices
        # Envia o catálogo inteiro. O Gemini tem até 2 Milhões de tokens de janela!
        amostra_catalogo = json.dumps(self.catalogo, ensure_ascii=False)
        
        prompt_rastreador = f"""
        Você é um agente especial de tribunal mapeador de processos (Vectorless Reasoning RAG).
        O Usuário perguntou: "{query}"
        
        Aqui está o CATÁLOGO com as chaves e resumos preliminares dos Acórdãos:
        {amostra_catalogo}
        
        Pense passo a passo. Quais são as {k} chaves de processos (ex: "815/2026") que parecem ter a resposta?
        Responda APENAS com um Array JSON de strings: ["chave1", "chave2"]. Sem marcação markdown ou texto extra.
        Se não achar nada, retorne [].
        """
        
        client_info = self._iniciar_cliente(api_key, modelo_escolhido)
        provider = client_info["provider"]
        client = client_info["client"]
        
        print(f"\n[RAG] {provider.upper()} Lendo o Catálogo offline e estruturando a árvore de busca...")
        try:
            if provider == "google":
                resposta = client.models.generate_content(
                    model=modelo_escolhido,
                    contents=prompt_rastreador,
                )
                raw_text = resposta.text
            elif provider == "openai":
                resposta = client.chat.completions.create(
                    model=modelo_escolhido,
                    messages=[{"role": "user", "content": prompt_rastreador}],
                    temperature=0.1
                )
                raw_text = resposta.choices[0].message.content
            elif provider == "anthropic":
                resposta = client.messages.create(
                    model=modelo_escolhido,
                    messages=[{"role": "user", "content": prompt_rastreador}],
                    max_tokens=1000,
                    temperature=0.1
                )
                raw_text = resposta.content[0].text

            # Extração segura de JSON ignorando baboseiras da IA
            import re
            match = re.search(r'\[.*\]', raw_text.strip().replace('\n', ''), re.DOTALL)
            if match:
                chaves_selecionadas = json.loads(match.group(0))
            else:
                try:
                    chaves_selecionadas = json.loads(raw_text.strip().replace('```json', '').replace('```', '').strip())
                except:
                    chaves_selecionadas = []
            
            # Etapa 2: Recupera a íntegra (não chunkada!) das decisões por Python (O pulo do gato)
            if not chaves_selecionadas:
                return {
                    "documentos": ["Nenhum acórdão compatível encontrado no catálogo inicial."],
                    "prompt_final": f"Usuário perguntou: {query}\n\nNenhuma base de apoio localizada.",
                    "ids": []
                }
                
            texto_base = self.procurar_acordao_integra(chaves_selecionadas)
            
            prompt_final = f"""
Responda à pergunta "{query}".
Baseie-se 100% na íntegra dos seguintes acórdãos que você selecionou para leitura profuda:
{texto_base[:60000]}
"""
            
            return {
                "documentos": ["Acórdãos recuperados em íntegra na memória do modelo"],
                "prompt_final": prompt_final,
                "ids": chaves_selecionadas
            }
            
        except Exception as e:
            return {
                "documentos": [f"Erro na busca sintática: {str(e)}"],
                "prompt_final": query,
                "ids": []
            }
