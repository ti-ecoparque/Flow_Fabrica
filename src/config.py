import streamlit as st

def configurar_layout():
    """Configura o título e a largura total da página."""
    st.set_page_config(page_title="Visão Compras", layout="wide")

def checar_autenticacao():
    """Valida se o usuário está logado. Se não estiver, exibe a tela de login."""

    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:

        st.title("🔑 Acesso ao Sistema")

        with st.form("form_login"):

            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            botao_entrar = st.form_submit_button("Entrar")

            if botao_entrar:
                usuarios = st.secrets["credentials"]
                if (
                    usuario_input in usuarios
                    and usuarios[usuario_input] == senha_input
                ):
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario_input
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.stop()