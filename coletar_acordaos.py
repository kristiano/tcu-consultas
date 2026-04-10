"""
Coletor de Acórdãos do TCU via API Pública de Dados Abertos.

Estratégia inspirada em https://github.com/netoferraz/acordaos-tcu
mas utiliza a API REST oficial em vez de web crawling.

Uso:
    python coletar_acordaos.py --quantidade 500 --output data/acordaos.csv
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

import requests

API_BASE_URL = "https://dados-abertos.apps.tcu.gov.br/api/acordao"
ENDPOINT_RECUPERA = f"{API_BASE_URL}/recupera-acordaos"

# Campos que iremos extrair de cada acórdão
CAMPOS_CSV = [
    "anoProcLido",
    "anoAcordao",
    "numAcordao",
    "colegiado",
    "relator",
    "situacao",
    "numProc",
    "tipoProcesso",
    "dtSessao",
    "numAta",
    "interessadoReponsavelRecorrente",
    "entidade",
    "representanteMp",
    "unidadeTecnica",
    "representanteLegal",
    "assunto",
    "sumario",
    "acordao",
    "quorum",
    "urlAcordaoDoc",
    "urlAcordaoPdf",
]


def coletar_acordaos(quantidade_total: int = 500, lote: int = 50) -> list[dict]:
    """
    Coleta acórdãos da API do TCU em lotes.

    Args:
        quantidade_total: Total de acórdãos para coletar
        lote: Tamanho de cada lote (máx. permitido pela API)

    Returns:
        Lista de dicionários com os dados dos acórdãos
    """
    todos_acordaos = []
    inicio = 0

    while inicio < quantidade_total:
        qtd = min(lote, quantidade_total - inicio)
        params = {"inicio": inicio, "quantidade": qtd}

        print(f"  📥 Coletando acórdãos {inicio + 1} a {inicio + qtd}...")

        try:
            response = requests.get(ENDPOINT_RECUPERA, params=params, timeout=30)
            response.raise_for_status()
            dados = response.json()
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Erro na requisição (início={inicio}): {e}")
            print("  ⏳ Aguardando 5s antes de tentar novamente...")
            time.sleep(5)
            continue
        except ValueError:
            print(f"  ⚠️  Resposta não é JSON válido (início={inicio})")
            inicio += qtd
            continue

        if not dados:
            print("  ℹ️  Nenhum dado retornado. Fim da coleta.")
            break

        # Normalizar os registros para os campos esperados
        for registro in dados:
            acordao_normalizado = {}
            for campo in CAMPOS_CSV:
                valor = registro.get(campo, "")
                if valor is None:
                    valor = ""
                # Limpar quebras de linha para manter CSV íntegro
                if isinstance(valor, str):
                    valor = valor.replace("\n", " ").replace("\r", " ").strip()
                acordao_normalizado[campo] = valor
            todos_acordaos.append(acordao_normalizado)

        inicio += qtd
        # Pausa para não sobrecarregar a API (sem suporte a múltiplos acessos)
        time.sleep(1)

    return todos_acordaos


def salvar_csv(acordaos: list[dict], caminho: str) -> None:
    """Salva a lista de acórdãos em arquivo CSV."""
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)

    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        writer.writerows(acordaos)

    print(f"\n✅ {len(acordaos)} acórdãos salvos em: {caminho}")


def main():
    parser = argparse.ArgumentParser(
        description="Coleta acórdãos do TCU via API de Dados Abertos"
    )
    parser.add_argument(
        "--quantidade",
        type=int,
        default=500,
        help="Quantidade total de acórdãos a coletar (default: 500)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/acordaos.csv",
        help="Caminho do arquivo CSV de saída (default: data/acordaos.csv)",
    )
    parser.add_argument(
        "--lote",
        type=int,
        default=50,
        help="Tamanho do lote por requisição (default: 50)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🏛️  Coletor de Acórdãos do TCU")
    print(f"   Quantidade: {args.quantidade}")
    print(f"   Saída: {args.output}")
    print(f"   Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    acordaos = coletar_acordaos(args.quantidade, args.lote)

    if acordaos:
        salvar_csv(acordaos, args.output)
    else:
        print("\n❌ Nenhum acórdão coletado. Verifique a conexão e tente novamente.")
        sys.exit(1)


if __name__ == "__main__":
    main()
