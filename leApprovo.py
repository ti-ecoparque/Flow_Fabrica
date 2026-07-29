import json
import toml
import requests
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client

config = toml.load(".streamlit/secrets.toml")
#print(config)

SUPABASE_URL = config["SUPABASE_URL"]
SUPABASE_KEY = config["SUPABASE_KEY"]

#APPROVO_COOKIE = config["APPROVO"]["COOKIE"]
APPROVO_COOKIE = config["APPROVO"]["APPROVO_COOKIE"]

COOKIES = {
    "Approvo": APPROVO_COOKIE
}

APPROVO_DOCUMENTS_URL = config["APPROVO"]["APPROVO_DOCUMENTS_URL"]

APPROVO_OCCURRENCES_URL = config["APPROVO"]["APPROVO_OCCURRENCES_URL"]

APPROVO_VALIDATE_URL = config["APPROVO"]["APPROVO_VALIDATE_URL"]


HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    )
}

fim = datetime.today()
inicio = fim - timedelta(days=30)

DATA_INICIO = inicio.strftime("%d/%m/%Y")
DATA_FIM = fim.strftime("%d/%m/%Y")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

def processar_ocorrencias():
    """Rotina para processar o novo relatório de Ocorrências."""
    print("\n--- PROCESSANDO REPORT: OCCURRENCES ---")
    url = "https://approvoecoparque.megaerp.online/React/src/indicadores/WebMethods.aspx/GetOccurrencesReport"
    
    dados_brutos = extrair_dados_api(url)
    if not dados_brutos:
        print("Nenhum dado de ocorrência encontrado.")
        return

    df = pd.DataFrame(dados_brutos)
    
    # Desduplicação inteligente com base nas chaves exclusivas da ocorrência
    df = df.drop_duplicates(subset=["chave_completa", "nome_aprovador"])

    # Conversão de Tipos específicos de Ocorrências
    df["codigo_aplicacao"] = pd.to_numeric(df["codigo_aplicacao"], errors="coerce").astype("Int64")
    df["numero_documento"] = pd.to_numeric(df["numero_documento"], errors="coerce").astype("Int64")
    df["valor_documento"] = pd.to_numeric(df["valor_documento"], errors="coerce").astype("float64")

    # Tratamento de Timestamps e Datas
    df["data_ocorrencia"] = pd.to_datetime(df["data_ocorrencia"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    df["data_documento"] = pd.to_datetime(df["data_documento"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["data_sincronizacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = df.astype(object).where(pd.notnull(df), None)
    registros = df.to_dict("records")

    enviar_supabase("rel_approvo_ocorrencias", registros, "chave_completa,nome_aprovador")

def processar_documentos():
    """Rotina para processar o relatório clássico de Documentos."""
    print("\n--- PROCESSANDO REPORT: DOCUMENTS ---")
    url = "https://approvoecoparque.megaerp.online/React/src/indicadores/WebMethods.aspx/GetDocumentsReport"
    
    dados_brutos = extrair_dados_api(url)
    if not dados_brutos:
        print("Nenhum dado de documento encontrado.")
        return

    df = pd.DataFrame(dados_brutos)
    df = df.drop_duplicates(subset=["doc_in_codigo", "numero_documento"])

    # Conversão de Tipos
    colunas_int = ["doc_in_codigo", "pai_doc_in_codigo", "codigo_aplicacao", "numero_documento", "codigo_solicitante"]
    for col in colunas_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["data_documento"] = pd.to_datetime(df["data_documento"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["data_envio"] = pd.to_datetime(df["data_envio"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    df["data_sincronizacao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = df.astype(object).where(pd.notnull(df), None)
    registros = df.to_dict("records")

    enviar_supabase("rel_approvo", registros, "doc_in_codigo,numero_documento")

def validar_sessao():
    """Valida se o cookie do Approvo está ativo."""
    
    print("Validando sessão no Approvo...")

    teste = requests.get(
        "https://approvoecoparque.megaerp.online/Indicadores/indicadores.aspx",
        cookies=COOKIES,
        timeout=30
    )

    print(f"Status recebido: {teste.status_code}")

    if teste.status_code != 200:
        raise Exception(
            f"Cookie inválido ou expirado. Status recebido: {teste.status_code}"
        )

    print("Sessão validada com sucesso.")


def enviar_supabase(tabela, registros, chaves_conflito):
    """Envia os registros formatados em lotes para o Supabase usando UPSERT."""
    LOTE = 500
    total = len(registros)
    print(f"Iniciando envio de {total} registros para a tabela '{tabela}'...")
    
    for i in range(0, total, LOTE):
        lote = registros[i:i + LOTE]
        supabase.table(tabela).upsert(
            lote,
            on_conflict=chaves_conflito
        ).execute()
        print(f"Progresso '{tabela}': {min(i + LOTE, total)}/{total} enviados.")

def extrair_dados_api(endpoint_url):
    """Realiza a paginação e extração genérica de dados da API."""
    todos_registros = []
    pagina = 1

    while True:
        payload = {
            "filtros": [109, "A", 104, 30, DATA_INICIO, DATA_FIM, None, None, None, None, None, None, None, None, None],
            "pagination": pagina
        }

        response = requests.post(
            endpoint_url,
            json=payload,
            headers=HEADERS,
            cookies=COOKIES,
            timeout=60
        )
        response.raise_for_status()
        
        dados = json.loads(response.json()["d"])
        print(f"Página {pagina}: {len(dados)} registros encontrados.")

        if len(dados) == 0:
            break

        todos_registros.extend(dados)
        pagina += 1

    return todos_registros


def processar_approvo():

    print(
        f"Período de Execução: "
        f"{DATA_INICIO} até {DATA_FIM}"
    )

    try:

        validar_sessao()
        processar_documentos()
        processar_ocorrencias()

        print(
            "\n✅ Processo de sincronização "
            "concluído."
        )

    except Exception as e:

        print(
            f"\n❌ Erro no Approvo: {e}"
        )
        
if __name__ == "__main__":
    processar_approvo()
        