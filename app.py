import streamlit as st
from groq import Groq

# 1. PEGAR A CHAVE AUTOMATICAMENTE DOS SECRETS
# Isso faz com que ninguém precise digitar a chave no site
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("Erro: Configure a GROQ_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 2. VISUAL ORIGINAL DO TERMINAL
st.title("📟 Terminal Macro ICT")
st.markdown("---")

# Se você tinha uma lista de temas no código original, ela continua aqui
tema = st.selectbox("Selecione o Fluxo de Análise:", [
    "Fluxo 1", "Fluxo 2", "Fluxo 3", "Fluxo 4", "Fluxo 5", "Fluxo 6", "Fluxo 7"
])

# Espaço para o usuário digitar
pergunta = st.text_area("Digite sua análise ou dúvida aqui:", height=150)

if st.button("Executar"):
    if pergunta:
        with st.spinner("Processando..."):
            try:
                # O sistema usa a SUA api_key configurada nos bastidores
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": f"Você é um especialista em ICT focado no {tema}."},
                        {"role": "user", "content": pergunta}
                    ],
                    model="llama3-8b-8192",
                )
                
                # Exibe a resposta
                st.markdown("### 📝 Resultado:")
                st.write(chat_completion.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro na IA: {e}")
    else:
        st.warning("Por favor, digite algo antes de executar.")

st.markdown("---")
st.caption("Terminal Online - Acesso Liberado")
