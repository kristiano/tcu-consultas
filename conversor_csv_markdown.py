import pandas as pd
import sys
import os
import argparse

import csv

def conversor(csv_path, saida_md="acordaos.md"):
    if not os.path.exists(csv_path):
        print(f"Erro: Arquivo {csv_path} não encontrado.")
        sys.exit(1)
        
    print(f"Lendo base {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep='|', quoting=csv.QUOTE_NONE, on_bad_lines='skip', engine='python')
    except Exception as e:
        print(f"Tentando modo tolerante extremo... Erro nativo: {e}")
        df = pd.read_csv(csv_path, sep='|', quoting=csv.QUOTE_NONE, on_bad_lines='warn', engine='python')
    
    
    # Padronizando colunas mas de forma branda, já que você vai mandar o arquivo sujo
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('ã', 'a').str.replace('ó', 'o')
    
    print(f"Gerando Markdown com {len(df)} acórdãos para o PageIndex ler...")
    
    with open(saida_md, "w", encoding="utf-8") as f:
        f.write("# Base de Jurisprudência TCU\n\n")
        
        for idx, row in df.iterrows():
            # Tenta pegar chaves famosas do TCU (acordao, ano, data), ou fallback para índice na tabela
            num = row.get("acordao", row.get("numero", row.get("num_acordao", f"ID_{idx}")))
            ano = row.get("ano", row.get("ano_acordao", ""))
            titulo = f"Acórdão {num}/{ano}" if ano else f"Decisão {num}"
            
            f.write(f"## {titulo}\n\n")
            
            # Tudo que for texto gigante ganha nível H3 (###) para o algoritmo da VectifyAI hierarquizar no RAG
            for col in df.columns:
                if col not in ["acordao", "ano", "numero", "num_acordao", "ano_acordao"]:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != "":
                        f.write(f"### {col.capitalize()}\n")
                        f.write(f"{str(val).strip()}\n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Converte CSV do TCU para um grande Markdown hierárquico usado pelo PageIndex")
    parser.add_argument("--input", "-i", type=str, required=True, help="Caminho do seu arquivo .csv")
    parser.add_argument("--output", "-o", type=str, default="acordaos_tcu.md", help="Arquivo Markdown exportado")
    args = parser.parse_args()
    
    conversor(args.input, args.output)
    print(f"✅ Arquivo {args.output} gerado! O PageIndex agora consegue entender a hierarquia dos julgamentos.")
