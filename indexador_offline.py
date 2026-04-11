import os
import faiss
import pickle
import numpy as np
import pandas as pd
import argparse
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import firebase_admin
from firebase_admin import credentials, storage

# ─── Configurações ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
MAX_TOKENS_PER_CHUNK = 500
BATCH_SIZE = 64

def limpar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza as colunas de vários tipos de CSV (Kaggle ou Oficial)"""
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
    
    return df.rename(columns=col_map)

def construir_texto(row) -> str:
    """Constrói o texto base que será transformado em vetor (Embedding)"""
    partes = []
    
    titulo = row.get("tituloAcordao", "")
    num = row.get("numAcordao", "")
    ano = row.get("anoAcordao", "")
    colegiado = row.get("colegiado", "")
    
    titulo_final = titulo if titulo else f"Acórdão {num}/{ano} - {colegiado}"
    partes.append(str(titulo_final))

    for campo, label in [
        ("relator", "Relator"),
        ("tipoProcesso", "Tipo de Processo"),
        ("assunto", "Assunto"),
        ("entidade", "Entidade"),
    ]:
        valor = row.get(campo, "")
        if pd.notna(valor) and valor != "":
            partes.append(f"{label}: {valor}")

    sumario = row.get("sumario", "")
    if pd.notna(sumario) and sumario != "":
        partes.append(f"Sumário: {sumario}")

    texto_completo = "\n".join(partes)
    # Limita ao tamanho heurístico de 2000 caracteres para evitar estourar local
    return texto_completo[:2000]

def upload_to_firebase(local_file: str, bucket_name: str):
    """Envia um arquivo local para o Firebase Storage"""
    bucket = storage.bucket(bucket_name)
    file_name = os.path.basename(local_file)
    blob = bucket.blob(file_name)
    print(f"⬆️ Fazendo upload do {file_name} para o Firebase Storage...")
    blob.upload_from_filename(local_file)
    print(f"✅ Upload de {file_name} concluído!")

def processar_csv(caminho_csv: str, output_dir: str, chunk_size: int = 10000):
    print("⏳ Carregando o Modelo IA de Vectorização...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    documentos = []
    
    arquivos_alvo = []
    if os.path.isdir(caminho_csv):
        arquivos_alvo = list(Path(caminho_csv).glob("*.csv"))
        print(f"📁 Diretório detectado. Encontrados {len(arquivos_alvo)} arquivos CSV para processar.")
    else:
        arquivos_alvo = [Path(caminho_csv)]
        print(f"📖 Lendo o arquivo {caminho_csv} em modo Chunk...")
        
    chunk_count = 1
    
    for arquivo in arquivos_alvo:
        print(f"\n--- Iniciando arquivo: {arquivo.name} ---")
        try:
            reader = pd.read_csv(arquivo, encoding='utf-8', dtype=str, on_bad_lines='skip', chunksize=chunk_size)
        except UnicodeDecodeError:
            reader = pd.read_csv(arquivo, encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=chunk_size)
        
        for df_chunk in reader:
            print(f"Lote {chunk_count} [{arquivo.name}] ({len(df_chunk)} linhas)")
            df_chunk = df_chunk.fillna("")
            df_chunk = limpar_colunas(df_chunk)
            
            textos = []
            lote_docs = []
            
            for _, row in df_chunk.iterrows():
                texto = construir_texto(row)
                textos.append(texto)
                
                titulo = row.get("tituloAcordao", "")
                ano_ext = row.get("anoAcordao", "")
                if not ano_ext and titulo:
                    import re
                    match = re.search(r'/(\d{4})', str(titulo))
                    if match:
                        ano_ext = match.group(1)
                        
                doc = {
                    "texto": texto,
                    "metadados": {
                        "num_acordao": row.get("numAcordao", ""),
                        "ano": ano_ext,
                        "colegiado": row.get("colegiado", ""),
                        "relator": row.get("relator", ""),
                        "tipo_processo": row.get("tipoProcesso", ""),
                        "assunto": row.get("assunto", ""),
                        "sumario": row.get("sumario", ""),
                        "acordao": row.get("acordao", ""),
                        "entidade": row.get("entidade", ""),
                        "data_sessao": row.get("dtSessao", ""),
                        "processo": row.get("numProc", ""),
                        "titulo": str(row.get("tituloAcordao", "")),
                    },
                }
                lote_docs.append(doc)
            
            print("Trabalhando embeddings no processador local...")
            embeddings = model.encode(textos, batch_size=BATCH_SIZE, show_progress_bar=True, convert_to_numpy=True)
            embeddings = embeddings.astype("float32")
            
            index.add(embeddings)
            documentos.extend(lote_docs)
            
            chunk_count += 1

    Path(output_dir).mkdir(exist_ok=True)
    faiss_path = os.path.join(output_dir, "tcu_base.faiss")
    faiss.write_index(index, faiss_path)
    
    pkl_path = os.path.join(output_dir, "tcu_meta.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(documentos, f)
        
    print(f"🎉 ÊXITO! Index criados em: {output_dir}")
    print(f"- Total Acórdãos Indexados: {index.ntotal}")
    
    return faiss_path, pkl_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexador Offline do TCU - Converta CSV para IA e jogue no Firebase.")
    parser.add_argument("--csv", required=True, help="O arquivo CSV super pesado (ex: total-tcu.csv).")
    parser.add_argument("--out", default="data", help="Local para salvar os indices '.faiss' e '.pkl'.")
    parser.add_argument("--firebase-key", help="Arquivo JSON de conta de serviço Firebase (opcional).")
    parser.add_argument("--bucket", help="Nome do bucket do Firebase (só o nome, sem gsap://). Funciona junto de --firebase-key.")
    
    args = parser.parse_args()
    
    f_path, p_path = processar_csv(args.csv, args.out)
    
    if args.firebase_key and args.bucket:
        try:
            cred = credentials.Certificate(args.firebase_key)
            firebase_admin.initialize_app(cred, {'storageBucket': args.bucket})
            upload_to_firebase(f_path, args.bucket)
            upload_to_firebase(p_path, args.bucket)
            print("🚀 TUDO PRONTO NA NUVEM!")
        except Exception as e:
            print(f"❌ Falha ao logar no firebase ou criar upload: {e}")
