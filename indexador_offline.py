import pandas as pd
import json
import os
import sys
import firebase_admin
from firebase_admin import credentials, storage

def inicializar_firebase():
    """Inicializa o Firebase da mesma forma que os scripts antigos."""
    try:
        firebase_admin.get_app()
    except ValueError:
        if not os.path.exists('chaves-tcu.json'):
            print("Arquivo chaves-tcu.json não encontrado!")
            return None
        cred = credentials.Certificate('chaves-tcu.json')
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'tcu-app-426ad.appspot.com'
        })
    return storage.bucket()

def criar_catalogo_para_rag_sem_vetor(csv_path, output_json="catalogo_acordaos.json"):
    print(f"Lendo {csv_path} para extrair o Catálogo (Vectorless RAG)...")
    try:
        # Usa python engine e quote_none para lidar com as aspas sujas do CSV do TCU
        import csv
        df = pd.read_csv(csv_path, sep=',', quoting=csv.QUOTE_MINIMAL, on_bad_lines='skip', engine='python')
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return False
        
    df.columns = df.columns.str.strip().str.replace('"', '').str.lower().str.replace(' ', '_').str.replace('ã', 'a').str.replace('ó', 'o')
    
    catalogo = {}
    print("Construindo índice estruturado puramente em Python (Zero custo de tokens)...")
    
    for idx, row in df.iterrows():
        try:
            num = str(row.get("numacordao", row.get("acordao", f"ID_{idx}"))).replace('"', '')
            ano = str(row.get("anoacordao", row.get("ano", ""))).replace('"', '')
            chave = f"{num}/{ano}" if ano.strip() else f"ID_{idx}"
            
            # Limpa lixos HTML
            assunto = str(row.get("assunto", "")).replace('"', '').strip()
            relator = str(row.get("relator", "")).replace('"', '').strip()
            sumario = str(row.get("sumario", "")).replace('"', '').strip()
            
            # Evitar NaNs do pandas
            if assunto == "nan": assunto = ""
            if relator == "nan": relator = "Não informado"
            if sumario == "nan": sumario = ""
            
            # Pega um snippet do sumario para o LLM ter noçao do que é
            snippet = (sumario[:300] + '...') if len(sumario) > 300 else sumario
            
            origem = str(row.get("key", chave)).replace('"', '')
            
            catalogo[chave] = {
                "relator": relator,
                "assunto": assunto,
                "resumo": snippet,
                "arquivo_origem": origem
            }
        except:
            continue
            
    # Salva o catálogo localmente
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)
        
    print(f"Catálogo criado com sucesso: {len(catalogo)} acórdãos sumarizados.")
    return True

def upload_to_firebase(filename):
    bucket = inicializar_firebase()
    if not bucket:
        return
        
    blob = bucket.blob(filename)
    print(f"Fazendo upload de {filename} para o Firebase na raiz...")
    blob.upload_from_filename(filename)
    print(f"✅ Arquivo {filename} carregado no Firebase!")

if __name__ == "__main__":
    csv_file = "acordao2026-limpo.csv"
    json_file = "catalogo_acordaos.json"
    
    sucesso = criar_catalogo_para_rag_sem_vetor(csv_file, json_file)
    if sucesso:
        print("\nIniciando upload para provedor de nuvem (Firebase)...")
        upload_to_firebase(json_file)
        
        # Subimos o CSV brutão também para a nuvem? Para a arquitetura vectorless, o app precisará baixar
        # o texto completo sob demanda. Como o CSV é grande (100MB), o Streamlit Cloud vai estourar a RAM
        # se não fizermos stream. O App pode baixar apenas o necessário.
        print("\nPara a nova arquitetura sem vetores, você também precisa subir o CSV bruto para que a aplicação consiga pescar os textos originais completos sob demanda das chaves indicadas pela IA.")
        upload_to_firebase(csv_file)
        print("\nIndexação Offline (Vectorless RAG) concluída com sucesso! NENHUM token de IA foi gasto.")
    
