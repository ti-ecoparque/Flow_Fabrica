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

PASTA_XLS_RM = os.path.join(
        os.path.expanduser("~"),
        "ECOPARQUE BAIRROS INTEGRADOS LTDA",
        "ECOPARQUE MATRIZ - 10_MEGA",
        "XLS_req_material"
    )

PASTA_LOGS = "logs"
os.makedirs(PASTA_LOGS, exist_ok=True)

ARQUIVO_LOG = os.path.join(
    PASTA_LOGS,
    f"rm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)

def gerar_log_rm(arquivo, registros, arquivo_log):

    log = {
        "resumo": {
            "arquivo": arquivo,
            "registros": len(registros),
            "rms_distintas": len(
                set(str(r["rm"]) for r in registros)
            ),
            "materiais_distintos": len(
                set(str(r["mat"]) for r in registros)
            ),
            "processado_em": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        },
        "detalhes": []
    }

    for registro in registros:

        log["detalhes"].append({
            "arquivo": arquivo,
            "rm": registro["rm"],
            "seq_item": registro["seq_item"],
            "material": registro["mat"],
            "descricao": registro["desc_item"],
            "quantidade": registro["qtd_solicitada"],
            "usuario": registro["usuario_solicitante"],
            "data_emissao": registro["data_emissao"],
            "data_necessidade": registro["data_necessidade"]
        })

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

def registrar_historico_situacao(dados_formatados):

    registros_atuais = (
        supabase.table("rel_solicitacao_compras")
        .select(
            "rm,seq_item,mat,sit_item"
        )
        .execute()
    )

    mapa_atual = {
        (
            str(r["rm"]),
            int(r["seq_item"]),
            str(r["mat"])
        ): r
        for r in registros_atuais.data
    }

    historicos = []

    for registro in dados_formatados:

        chave = (
            str(registro["rm"]),
            int(registro["seq_item"]),
            str(registro["mat"])
        )

        registro_antigo = mapa_atual.get(chave)

        if not registro_antigo:
            continue

        situacao_antiga = (
            registro_antigo.get("sit_item") or ""
        ).strip()

        situacao_nova = (
            registro.get("sit_item") or ""
        ).strip()

        if (situacao_antiga != situacao_nova and situacao_nova.upper() == "BAIXADO"):

            existe = (
                supabase.table("rel_solicitacao_compras_hist")
                .select("id")
                .eq("rm", registro["rm"])
                .eq("seq_item", registro["seq_item"])
                .eq("mat", registro["mat"])
                .eq("situacao_nova", "BAIXADO")
                .limit(1)
                .execute()
            )
            if not existe.data:
                historicos.append({
                    "rm": registro["rm"],
                    "seq_item": registro["seq_item"],
                    "mat": registro["mat"],
                    "situacao_anterior": situacao_antiga,
                    "situacao_nova": situacao_nova
                })

    if historicos:
        (
            supabase.table("rel_solicitacao_compras_hist")
            .insert(historicos)
            .execute()
        )
        print(
            f"✅ Histórico gerado: "
            f"{len(historicos)} alterações)"
        )

def processar_rms():
    
    global total_arquivos
    global total_registros
    
    total_arquivos = 0
    total_registros = 0

    print("INICIANDO PROCESSAMENTO DE RMS")

    for arquivo in os.listdir(PASTA_XLS_RM):

        if not arquivo.lower().endswith((".xlsx", ".xls")):
            continue

        caminho_arquivo = os.path.join(
            PASTA_XLS_RM,
            arquivo
        )
        
        arquivo_log = os.path.join(
            PASTA_LOGS,
            f"{os.path.splitext(arquivo)[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        try:

            df_bruto = pd.read_excel(caminho_arquivo)

            mapeamento_colunas = {
                "Filial": "filial",
                "Nr. RM": "rm",
                "Nome Filial": "nome_filial",
                "Código da solicitação": "cod_solicitacao",
                "Sequencial do item": "seq_item",
                "Data de emissão": "data_emissao",
                "Situação do Item": "sit_item",
                "Código do item": "mat",
                "Descrição do item": "desc_item",
                "Quantidade solicitada": "qtd_solicitada",
                "Unidade": "unidade_medida",
                "Usuário solicitante": "usuario_solicitante",
                "Status da necessidade": "status_necessidade",
                "Código da cotação": "cod_cotacao",
                "Data de necessidade": "data_necessidade"
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
                subset=["rm", "seq_item", "mat"],
                how="any"
            )

            colunas_texto = [
                "filial",
                "rm",
                "nome_filial",
                "cod_solicitacao",
                "sit_item",
                "mat",
                "desc_item",
                "unidade_medida",
                "usuario_solicitante",
                "status_necessidade",
                "cod_cotacao"
            ]

            for coluna in colunas_texto:

                df_filtrado[coluna] = (
                    df_filtrado[coluna]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

            df_filtrado["seq_item"] = (
                pd.to_numeric(
                    df_filtrado["seq_item"],
                    errors="coerce"
                )
                .fillna(0)
                .astype(int)
            )

            df_filtrado["qtd_solicitada"] = (
                pd.to_numeric(
                    df_filtrado["qtd_solicitada"],
                    errors="coerce"
                )
                .fillna(0)
                .astype(float)
            )

            df_filtrado["data_emissao"] = (
                pd.to_datetime(
                    df_filtrado["data_emissao"],
                    errors="coerce"
                )
                .dt.strftime("%Y-%m-%d")
            )

            df_filtrado["data_necessidade"] = (
                pd.to_datetime(
                    df_filtrado["data_necessidade"],
                    errors="coerce"
                )
                .dt.strftime("%Y-%m-%d")
            )

            df_filtrado = df_filtrado.drop_duplicates()
            dados_formatados = df_filtrado.to_dict(
                orient="records"
            )

            if not dados_formatados:
                print(
                    f"⚠️ Nenhum registro válido "
                    f"em {arquivo}"
                )
                continue

            registrar_historico_situacao(
                dados_formatados
            )

            supabase.table(
                "rel_solicitacao_compras"
            ).upsert(
                dados_formatados,
                on_conflict="rm,seq_item,mat"
            ).execute()

            
            total_arquivos += 1
            total_registros += len(dados_formatados)

            print(
                f"✅ Arquivo processado: "
                f"{arquivo}"
            )

            print(
                f"✅ Registros enviados: "
                f"{len(dados_formatados)}"
            )

            
            gerar_log_rm(
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
    print("FIM PROCESSAMENTO RMS")
    print("========================================")
    print(f"Arquivos processados : {total_arquivos}")
    print(f"Registros enviados   : {total_registros}")
    print("========================================")


if __name__ == "__main__":
    processar_rms()