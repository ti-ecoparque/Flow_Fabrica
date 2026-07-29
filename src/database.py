import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def conectar_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["API_KEY"]
    return create_client(url, key)

def buscar_dados_view(filtros: dict) -> list:
    supabase = conectar_supabase()
    query = supabase.from_("vw_visao_consolidada").select("*")

    # Aplicação de filtros direto na API
    if filtros.get("rm_numero"):
        query = query.eq("rm_numero", filtros["rm_numero"])
    if filtros.get("pc_numero"):
        query = query.eq("pc_numero", filtros["pc_numero"])
    
    if filtros.get("pc_comprador"):
        query = query.ilike(
            "pc_comprador",
            f"%{filtros['pc_comprador']}%"
        )

    if filtros.get("rm_usuario_solicitante"):
        query = query.ilike("rm_usuario_solicitante", f"%{filtros['rm_usuario_solicitante']}%")
        
    if filtros.get("rm_especificacao"):
        query = query.ilike(
            "rm_especificacao",
            f"%{filtros['rm_especificacao']}%"
        )    
    
    if (
        filtros.get("rm_retroativo")
        and filtros["rm_retroativo"] != "Todos"
    ):
        query = query.eq(
            "rm_retroativo",
            filtros["rm_retroativo"]
        )
        
    if filtros.get("pc_status_descricao") and filtros["pc_status_descricao"] != "Todos":
        query = query.eq(
            "pc_status_descricao",
            filtros["pc_status_descricao"]
        )
        
    if filtros.get("rm_status_aprovacao") and filtros["rm_status_aprovacao"] != "Todos":
        status_map = {
            "Aprovado": "A",
            "Reprovado": "R",
            "Pendente": "P"
        }
        query = query.eq(
            "rm_status_aprovacao",
            status_map[filtros["rm_status_aprovacao"]]
        )
    
    if (filtros.get("rm_situacao_item") and filtros["rm_situacao_item"] != "Todos"):
        query = query.eq(
            "rm_situacao_item",
            filtros["rm_situacao_item"]
        )
    
    if filtros.get("possui_pc") == "Sim":

        query = query.not_.is_(
            "pc_numero",
            None
        )

    elif filtros.get("possui_pc") == "Não":

        query = query.is_(
            "pc_numero",
            None
        )

        
    if filtros.get("data_inicio"):
        query = query.gte("rm_data_emissao", filtros["data_inicio"].isoformat())
    if filtros.get("data_fim"):
        query = query.lte("rm_data_emissao", filtros["data_fim"].isoformat())

    # Paginação em lotes para superar o teto de 1000 registros do PostgREST
    todos_dados = []
    offset = 0
    tamanho_lote = 1000

    
    while True:
        resposta = query.range(offset, offset + tamanho_lote - 1).execute()

        if not resposta.data:
            break

        todos_dados.extend(resposta.data)

        if len(resposta.data) < tamanho_lote:
            break

        offset += tamanho_lote


    #for registro in todos_dados[:3]:
        #print(registro)

    return todos_dados

