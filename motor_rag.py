"""
Motor RAG (Retrieval-Augmented Generation) para Acórdãos do TCU.

Responsável por:
1. Carregar acórdãos de arquivos CSV
2. Gerar embeddings via OpenAI
3. Indexar com FAISS para busca vetorial
4. Recuperar documentos relevantes para o contexto do LLM
"""

import hashlib
import os
import pickle
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import pandas as pd
import tiktoken
from sentence_transformers import SentenceTransformer


# ─── Configurações ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
MAX_TOKENS_PER_CHUNK = 500
CACHE_DIR = Path(".cache")
DATA_DIR = Path("data")


# ─── Funções auxiliares ───────────────────────────────────────────────────────

def contar_tokens(texto: str, modelo: str = "cl100k_base") -> int:
    """Conta tokens de um texto usando tiktoken."""
    enc = tiktoken.get_encoding(modelo)
    return len(enc.encode(texto))


def gerar_hash_arquivo(caminho: str) -> str:
    """Gera hash MD5 do arquivo para invalidação de cache."""
    h = hashlib.md5()
    with open(caminho, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── Classe Principal ────────────────────────────────────────────────────────

class MotorRAG:
    """Motor de Retrieval-Augmented Generation para acórdãos do TCU usando Embeddings locais."""

    def __init__(self):
        self.index: Optional[faiss.IndexFlatL2] = None
        self.documentos: list[dict] = []
        # Lazy loading do modelo de embeddings local para maior eficiência
        self._embedding_model = None
        CACHE_DIR.mkdir(exist_ok=True)
        
    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedding_model

    # ─── Carregamento de dados ────────────────────────────────────────────

    def carregar_csvs(self, diretorio: str = "data") -> pd.DataFrame:
        """
        Carrega todos os CSVs de um diretório e consolida em um DataFrame.
        """
        dfs = []
        dir_path = Path(diretorio)

        if not dir_path.exists():
            raise FileNotFoundError(
                f"Diretório '{diretorio}' não encontrado."
            )

        csv_files = list(dir_path.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(
                f"Nenhum arquivo CSV encontrado em '{diretorio}'."
            )

        for csv_file in csv_files:
            try:
                # Tentar UTF-8, cair para latin1 se falhar
                try:
                    df = pd.read_csv(csv_file, encoding="utf-8", dtype=str)
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_file, encoding="latin1", dtype=str)
                
                df = df.fillna("")
                
                # Normalizar colunas do Kaggle/Tcu dataset para os nomes internos
                col_map = {}
                for col in df.columns:
                    col_lower = col.strip().lower()
                    if "título" in col_lower or "t¿tulo" in col_lower or "ttulo" in col_lower:
                        col_map[col] = "tituloAcordao"
                    elif "data" in col_lower:
                        col_map[col] = "dtSessao"
                    elif "relator" in col_lower:
                        col_map[col] = "relator"
                    elif "sumário" in col_lower or "sum¿rio" in col_lower or "sumrio" in col_lower:
                        col_map[col] = "sumario"
                    elif "tipo de processo" in col_lower:
                        col_map[col] = "tipoProcesso"
                    elif "processo" in col_lower and "tipo" not in col_lower:
                        col_map[col] = "numProc"
                    elif "assunto" in col_lower:
                        col_map[col] = "assunto"
                    elif "entidade" in col_lower:
                        col_map[col] = "entidade"
                
                df = df.rename(columns=col_map)
                dfs.append(df)
            except Exception as e:
                print(f"⚠️ Erro ao carregar {csv_file}: {e}")

        if not dfs:
            raise ValueError("Nenhum CSV carregado com sucesso.")

        df_completo = pd.concat(dfs, ignore_index=True)
        return df_completo

    # ─── Preparação de documentos ─────────────────────────────────────────

    def preparar_documentos(self, df: pd.DataFrame) -> list[dict]:
        """
        Transforma cada acórdão em um documento com texto combinado
        para geração de embedding.
        """
        documentos = []

        for _, row in df.iterrows():
            # Montar texto rico para embedding semântico
            partes = []

            # Identificação
            titulo = row.get("tituloAcordao", "")
            num = row.get("numAcordao", "")
            ano = row.get("anoAcordao", "")
            colegiado = row.get("colegiado", "")
            
            titulo_final = titulo if titulo else f"Acórdão {num}/{ano} - {colegiado}"
            partes.append(titulo_final)

            # Metadados
            for campo, label in [
                ("relator", "Relator"),
                ("tipoProcesso", "Tipo de Processo"),
                ("assunto", "Assunto"),
                ("entidade", "Entidade"),
            ]:
                valor = row.get(campo, "")
                if valor:
                    partes.append(f"{label}: {valor}")

            # Conteúdo principal
            sumario = row.get("sumario", "")
            if sumario:
                partes.append(f"Sumário: {sumario}")

            acordao_texto = row.get("acordao", "")
            if acordao_texto:
                partes.append(f"Decisão: {acordao_texto}")

            texto_completo = "\n".join(partes)

            # Truncar se necessário
            if contar_tokens(texto_completo) > MAX_TOKENS_PER_CHUNK:
                enc = tiktoken.get_encoding("cl100k_base")
                tokens = enc.encode(texto_completo)[:MAX_TOKENS_PER_CHUNK]
                texto_completo = enc.decode(tokens)

            # Extrair ano para estatísticas, se possível, a partir da Título
            ano_ext = ano
            if not ano_ext and titulo:
                # Tentar encontrar /20NN
                import re
                match = re.search(r'/(\d{4})', titulo)
                if match:
                    ano_ext = match.group(1)

            doc = {
                "texto": texto_completo,
                "metadados": {
                    "num_acordao": num,
                    "ano": ano_ext,
                    "colegiado": colegiado,
                    "relator": row.get("relator", ""),
                    "tipo_processo": row.get("tipoProcesso", ""),
                    "assunto": row.get("assunto", ""),
                    "sumario": sumario,
                    "acordao": acordao_texto,
                    "entidade": row.get("entidade", ""),
                    "data_sessao": row.get("dtSessao", ""),
                    "processo": row.get("numProc", ""),
                    "titulo": titulo_final,
                },
            }
            documentos.append(doc)

        self.documentos = documentos
        return documentos

    # ─── Embeddings ───────────────────────────────────────────────────────

    def gerar_embeddings(self, textos: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Gera embeddings dos textos usando modelo local em lotes.
        """
        textos = [t if t.strip() else "sem conteúdo" for t in textos]
        
        # Gerar os embeddings usando batching eficiente da biblioteca
        embeddings = self.embedding_model.encode(
            textos, 
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        return embeddings.astype("float32")

    # ─── Indexação FAISS ──────────────────────────────────────────────────

    def construir_indice(
        self, documentos: Optional[list[dict]] = None, usar_cache: bool = True
    ) -> None:
        """
        Constrói o índice FAISS a partir dos documentos.
        Usa cache para evitar recálculo de embeddings desnecessário.
        """
        if documentos:
            self.documentos = documentos

        if not self.documentos:
            raise ValueError("Nenhum documento carregado para indexação.")

        # Verificar cache
        cache_path = CACHE_DIR / "faiss_index.pkl"
        docs_hash = hashlib.md5(
            str([d["texto"][:100] for d in self.documentos]).encode()
        ).hexdigest()
        hash_path = CACHE_DIR / "docs_hash.txt"

        if usar_cache and cache_path.exists() and hash_path.exists():
            hash_salvo = hash_path.read_text().strip()
            if hash_salvo == docs_hash:
                with open(cache_path, "rb") as f:
                    cache = pickle.load(f)
                self.index = cache["index"]
                self.documentos = cache["documentos"]
                return

        # Gerar embeddings
        textos = [d["texto"] for d in self.documentos]
        embeddings = self.gerar_embeddings(textos)

        # Construir índice L2
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        self.index.add(embeddings)

        # Salvar cache
        with open(cache_path, "wb") as f:
            pickle.dump(
                {"index": self.index, "documentos": self.documentos}, f
            )
        hash_path.write_text(docs_hash)

    # ─── Busca semântica ──────────────────────────────────────────────────

    def buscar(self, consulta: str, top_k: int = 5) -> list[dict]:
        """
        Realiza busca semântica no índice FAISS.

        Args:
            consulta: Texto da consulta do usuário
            top_k: Número de resultados mais relevantes

        Returns:
            Lista de documentos relevantes com score de similaridade
        """
        if self.index is None:
            raise RuntimeError("Índice não construído. Execute construir_indice() primeiro.")

        # Embedding da consulta
        query_embedding = self.gerar_embeddings([consulta])

        # Busca no FAISS
        distances, indices = self.index.search(query_embedding, top_k)

        resultados = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documentos):
                doc = self.documentos[idx].copy()
                doc["score"] = float(dist)
                resultados.append(doc)

        return resultados

    # ─── Montagem de contexto para o LLM ──────────────────────────────────

    def montar_contexto(self, resultados: list[dict], max_tokens: int = 3000) -> str:
        """
        Monta o contexto RAG a partir dos resultados da busca
        para enviar ao LLM.
        """
        contexto_parts = []
        tokens_usados = 0

        for i, doc in enumerate(resultados, 1):
            meta = doc["metadados"]
            bloco = f"""
═══ Acórdão {i} ═══
📋 Identificação: {meta.get('titulo', 'N/A')}
👤 Relator: {meta.get('relator', 'N/A')}
📁 Processo: {meta.get('processo', 'N/A')}
📂 Tipo: {meta.get('tipo_processo', 'N/A')}
📅 Data Sessão: {meta.get('data_sessao', 'N/A')}
🏢 Entidade: {meta.get('entidade', 'N/A')}
📝 Assunto: {meta.get('assunto', 'N/A')}

📄 Sumário:
{meta.get('sumario', 'Não disponível')}
"""
            if meta.get('acordao'):
                bloco += f"\n⚖️ Decisão:\n{meta.get('acordao')}\n"
            bloco_tokens = contar_tokens(bloco)
            if tokens_usados + bloco_tokens > max_tokens:
                break
            contexto_parts.append(bloco)
            tokens_usados += bloco_tokens

        return "\n".join(contexto_parts)

    # ─── Pipeline completo ────────────────────────────────────────────────

    def inicializar(self, diretorio_dados: str = "data") -> int:
        """
        Pipeline completo: carrega CSVs → prepara documentos → indexa.

        Returns:
            Número de documentos indexados
        """
        df = self.carregar_csvs(diretorio_dados)
        docs = self.preparar_documentos(df)
        self.construir_indice(docs)
        return len(docs)

    # ─── Estatísticas ─────────────────────────────────────────────────────

    def estatisticas(self) -> dict:
        """Retorna estatísticas da base indexada."""
        if not self.documentos:
            return {"total": 0}

        anos = [d["metadados"].get("ano", "") for d in self.documentos if d["metadados"].get("ano")]
        colegiados = [d["metadados"].get("colegiado", "") for d in self.documentos if d["metadados"].get("colegiado")]
        relatores = [d["metadados"].get("relator", "") for d in self.documentos if d["metadados"].get("relator")]

        return {
            "total": len(self.documentos),
            "anos": sorted(set(anos)),
            "colegiados": sorted(set(colegiados)),
            "total_relatores": len(set(relatores)),
        }
