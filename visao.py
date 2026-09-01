import streamlit as st
import datetime
from src.config import configurar_layout, checar_autenticacao
from src.database import buscar_dados_view, buscar_usuarios_unicos
from src.processing import processar_dataframe_compras
from src.components.grid import criar_multiindex_compras, destacar_rm
from src.components.styles import aplicar_estilo_grid

# Inicialização e Proteção de Rota
configurar_layout()
checar_autenticacao()

# Barra lateral de controle
if st.sidebar.button("Sair / Logout"):
    st.session_state.autenticado = False
    st.rerun()

# Cabeçalhos do painel
st.subheader("🛒 Filtros de Monitoramento")

# Definição das datas padrão
data_hoje = datetime.date.today()
trinta_dias_atras = data_hoje - datetime.timedelta(days=30)

# --- CARREGAR LISTA DE USUÁRIOS PARA O FILTRO (NOVO & OTIMIZADO) ---
lista_usuarios = buscar_usuarios_unicos()

# Bloco Visual 1: Construção dos Inputs na Interface
c1, c2, c3, c4 = st.columns(4)

filtro_rm = c1.text_input(
    "Número da RM:",
    key="filtro_rm"
)

filtro_pc = c2.text_input(
    "Número do Pedido (PC):",
    key="filtro_pc"
)

filtro_comprador = c3.text_input(
    "Comprador (Pedido):",
    key="filtro_comprador"
)

# ALTERADO: Mudança de campo de texto para Seleção Múltipla (Lista)
filtro_req = c4.multiselect(
    "Requisitante do Material:",
    options=lista_usuarios,
    default=[],
    key="filtro_req",
    placeholder="Selecione os usuários..."
)

c5, c6, c7, c8 = st.columns(4)
c9, c10, c11 = st.columns([3, 3, 1])
c12, c13 = st.columns(2)

data_ini = c7.date_input(
    "Data Emissão RM (Início):",
    value=trinta_dias_atras,
    format="DD/MM/YYYY",
    key="data_ini"
)

data_fim = c8.date_input(
    "Data Emissão RM (Fim):",
    value=data_hoje,
    format="DD/MM/YYYY",
    key="data_fim"
)

filtro_sit = c5.selectbox(
    "Situação do Pedido:",
    ["Todos", "Pendente", "Aprovado", "Reprovado"],
    key="filtro_sit"
)

filtro_status = c6.selectbox(
    "Status do Documento (App):",
    ["Todos", "Aprovado", "Reprovado", "Pendente"],
    key="filtro_status"
)

filtro_baixa = c9.selectbox(
    "Status da Baixa:",
    ["Todos", "Aberto", "Baixado", "Pendente", "Aprovar Estoque"],
    key="filtro_baixa"
)

filtro_possui_pc = c10.selectbox(
    "Possui Pedido de Compra?",
    ["Todos", "Sim", "Não"],
    key="filtro_possui_pc"
)

c11.markdown(
    "<div style='height:26px'></div>",
    unsafe_allow_html=True
)

limpar_filtros = c11.button(
    "🧹 Limpar",
    use_container_width=True
)

filtro_especificacao = c12.text_input(
    "Buscar Especificação:",
    key="filtro_especificacao"
)

filtro_retroativo = c13.selectbox(
    "Retroativo:",
    ["Todos", "Sim", "Não"],
    key="filtro_retroativo"
)

if limpar_filtros:
    for chave in [
        "filtro_rm",
        "filtro_pc",
        "filtro_comprador",
        "filtro_req",
        "filtro_sit",
        "filtro_status",
        "filtro_baixa",
        "filtro_possui_pc",
        "filtro_especificacao",
        "filtro_retroativo",
        "data_ini",
        "data_fim"
    ]:
        if chave in st.session_state:
            del st.session_state[chave]
    st.rerun()

# Validação do filtro numérico do Pedido de Compra
if filtro_pc and not filtro_pc.isdigit():
    st.warning("Por favor, digite apenas números no campo de Pedido (PC).")
    st.stop()

# Junta os valores capturados em um dicionário de filtros estruturado
dicionario_filtros = {
    "rm_numero": filtro_rm,
    "pc_numero": int(filtro_pc) if filtro_pc else None,
    "pc_comprador": filtro_comprador,
    "rm_usuario_solicitante": filtro_req,  # Agora envia a lista selecionada
    "rm_especificacao": filtro_especificacao,
    "rm_retroativo": filtro_retroativo,
    "pc_status_descricao": filtro_sit,
    "rm_status_aprovacao": filtro_status,
    "rm_situacao_item": filtro_baixa,
    "possui_pc": filtro_possui_pc,
    "data_inicio": data_ini,
    "data_fim": data_fim
}

# Bloco 2: Execução das Regras e Consulta
with st.spinner("Buscando dados na View consolidada..."):
    try:
        dados_banco = buscar_dados_view(dicionario_filtros)
        df_final = processar_dataframe_compras(dados_banco)
    except Exception as e:
        st.error("Erro no processamento de dados do aplicativo:")
        st.code(str(e))
        st.stop()

# Bloco Visual 3: Renderização da Tabela de Resultados Estilizada
if not df_final.empty:
    st.write(f"**{len(df_final)}** registros encontrados.")

    st.markdown(
        aplicar_estilo_grid(),
        unsafe_allow_html=True
    )

    df_exibicao = criar_multiindex_compras(df_final)

    df_estilizado = (
        df_exibicao.style
        .apply(destacar_rm, axis=None)
    )

    st.dataframe(
        df_estilizado,
        width="stretch",
        hide_index=True
    )
else:
    st.warning(
        "Nenhum dado encontrado para os filtros selecionados."
    )
