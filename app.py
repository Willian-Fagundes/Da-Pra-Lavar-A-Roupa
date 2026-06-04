from utils import resumo_streamlit, tratar_cep
import streamlit as st

st.title("Da pra lavar a roupa ?", text_alignment="center")
st.header("Veja o resumo dos próximos 5 dias.", text_alignment="center")

with st.form(key="formulario_cep"):
    cep_input = st.text_input(
        label="Digite o seu CEP:",
        placeholder="Ex: 01310-200 ou 01310200",
        max_chars=9, 
    )

    botao_enviar = st.form_submit_button(label="Resumo")

if botao_enviar:
    if cep_input.strip() == "":
        st.warning("Por favor, digite um CEP antes de enviar.")
    else:
        try:
            cidade, uf = tratar_cep(cep_input)
            resumo_streamlit(cidade, uf)

        except ValueError as erro:
            # Retorna a mensagem de erro customizada caso a validação falhe
            st.error(str(erro))