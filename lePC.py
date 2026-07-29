import os
import json
import pandas as pd
from datetime import datetime
from supabase import create_client
import toml


config = toml.load(".streamlit/secrets.toml")

SUPABASE_URL = config["SUPABASE_URL"]
SUPABASE_KEY = config["SUPABASE_KEY"]

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL ou SUPABASE_KEY não configuradas."
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


PASTA_XLS_PC = os.path.join(
    os.path.expanduser("~"),
    "ECOPARQUE BAIRROS INTEGRADOS LTDA",
    "ECOPARQUE MATRIZ - 10_MEGA",
    "XLS_ped_compra"
)

PASTA_LOGS = "logs"
os.makedirs(PASTA_LOGS, exist_ok=True)


def gerar_log_pc(
    arquivo,
    registros,
    arquivo_log
):

    log = {
        "resumo": {
            "arquivo": arquivo,
            "registros": len(registros),
            "pedidos_distintos": len(
                set(str(r["pedido"]) for r in registros)
            ),
            "materiais_distintos": len(
                set(str(r["mat"]) for r in registros)
            ),
            "processado_em": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        },
        "detalhes": registros
    }

    with open(
        arquivo_log,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            log,
            f,
            indent=4,
            ensure_ascii=False,
            default=str
        )


def processar_pedidos():

    global total_arquivos
    global total_registros

    total_arquivos = 0
    total_registros = 0

    print("========================================")
    print("INICIANDO PROCESSAMENTO PEDIDOS")
    print("========================================")

    for arquivo in os.listdir(PASTA_XLS_PC):

        if not arquivo.lower().endswith(
            (".xlsx", ".xls")
        ):
            continue

        caminho_excel = os.path.join(
            PASTA_XLS_PC,
            arquivo
        )

        arquivo_log = os.path.join(
            PASTA_LOGS,
            f"{os.path.splitext(arquivo)[0]}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        try:

            print(f"📖 Lendo: {arquivo}")

            df_bruto = pd.read_excel(
                caminho_excel
            )

            mapeamento_colunas = {
                "Número do pedido": "pedido",
                "Nome Filial": "nome_filial",
                "Cód. Item": "mat",
                "Nr.Processo": "nr_processos",
                "Situação do Item": "situacao_pedido",
                "Nome Fantasia": "nome_fantasia",
                "Total Pedido Compra": "total_pedido",
                "Item Pedido": "item_pedido",
                "Descrição do Item": "desc_item",
                "Quantidade": "quantidade"
            }

            colunas_faltantes = [
                col
                for col in mapeamento_colunas.keys()
                if col not in df_bruto.columns
            ]

            if colunas_faltantes:

                print(
                    f"❌ Colunas faltantes: "
                    f"{colunas_faltantes}"
                )

                continue

            df_filtrado = df_bruto[
                list(mapeamento_colunas.keys())
            ].copy()

            df_filtrado = df_filtrado.rename(
                columns=mapeamento_colunas
            )

            df_filtrado = df_filtrado.dropna(
                subset=[
                    "pedido",
                    "item_pedido",
                    "mat"
                ],
                how="all"
            )

            colunas_texto = [
                "pedido",
                "nome_filial",
                "mat",
                "nr_processos",
                "situacao_pedido",
                "nome_fantasia",
                "item_pedido",
                "desc_item"
            ]

            for coluna in colunas_texto:

                df_filtrado[coluna] = (
                    df_filtrado[coluna]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

            df_filtrado["quantidade"] = (
                pd.to_numeric(
                    df_filtrado["quantidade"],
                    errors="coerce"
                )
                .fillna(0)
            )

            df_filtrado["total_pedido"] = (
                pd.to_numeric(
                    df_filtrado["total_pedido"],
                    errors="coerce"
                )
                .fillna(0)
            )

            total_antes = len(
                df_filtrado
            )

            df_filtrado = (
                df_filtrado.drop_duplicates()
            )

            total_depois = len(
                df_filtrado
            )

            if total_antes != total_depois:

                print(
                    f"🧹 Removidos "
                    f"{total_antes-total_depois} "
                    f"duplicados"
                )

            dados_formatados = (
                df_filtrado.to_dict(
                    orient="records"
                )
            )

            if not dados_formatados:

                print(
                    f"⚠️ Nenhum registro válido "
                    f"em {arquivo}"
                )

                continue

            supabase.table(
                "rel_pedido_compra"
            ).upsert(
                dados_formatados,
                on_conflict="pedido,item_pedido,mat"
            ).execute()

            total_arquivos += 1
            total_registros += len(
                dados_formatados
            )

            print(
                f"✅ Arquivo processado: "
                f"{arquivo}"
            )

            print(
                f"✅ Registros enviados: "
                f"{len(dados_formatados)}"
            )

            gerar_log_pc(
                arquivo,
                dados_formatados,
                arquivo_log
            )

        except Exception as erro:

            print(
                f"❌ Erro ao processar "
                f"{arquivo}"
            )

            print(erro)

    print("========================================")
    print("FIM PROCESSAMENTO PEDIDOS")
    print("========================================")
    print(f"Arquivos processados : {total_arquivos}")
    print(f"Registros enviados   : {total_registros}")
    print("========================================")


if __name__ == "__main__":
    processar_pedidos()