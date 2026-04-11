import os
import json
from google import genai
import sys

def test_rag():
    # Carrega a chave de API (Simulação sem a chave, apenas lê o tamanho)
    import streamlit as st
    with open("catalogo_acordaos.json", 'r', encoding='utf-8') as f:
        catalogo = json.load(f)
        
    print(f"Total keys in catalog: {len(catalogo)}")
    amostra_catalogo = json.dumps(catalogo, ensure_ascii=False)
    print(f"Tam do JSON: {len(amostra_catalogo)} caracteres")

    # Tokens estimates: usually 4 chars per token.
    print(f"Tokens estimados: {len(amostra_catalogo) // 4}")

if __name__ == "__main__":
    test_rag()
