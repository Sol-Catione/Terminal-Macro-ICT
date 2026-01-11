import streamlit as st
from groq import Groq

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Terminal Macro ICT", page_icon="📟", layout="wide")

# 2. CONEXÃO SEGURA COM A CHAVE API
try:
    # O sistema busca a chave nos Secrets para liberar o acesso público
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("Erro: Configure a GROQ_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 3. INTERFACE ORIGINAL
st.title("📟 Terminal Macro ICT")
st.markdown("---")

# Seus temas originais aprovados
temas_originais = {
    "📊 COT & Institutional Bias": "COT report institutional net positions Smart Money",
    "💱 Forex: ICT Majors": "DXY EURUSD USDJPY algorithmic price action",
    "📀 Metais & Liquidez": "gold silver liquidity pools silver bullet",
    "📈 Índices: S&P500 / Nasdaq (ICT)": "S&P500 Nasdaq ES NQ price action liquidity",
    "🛢️ Commodities: ICT Flow": "crude oil brent wti order flow institutional",
    "🌍 Geopolítica & Macro": "geopolitics global conflict trade wars",
    "🏦 Política Monetária (Interest Rates)": "central banks FED inflation interest rates",
    "🕒 Killzones & High Impact": "economic calendar NFP FOMC news volatility"
}

# Menu de seleção com seus nomes exatos
fluxo_selecionado = st.selectbox("Selecione o Fluxo de Análise:", list(temas_originais.keys()))

# Área de texto para o usuário
user_input = st.text_area("Digite sua análise ou dúvida aqui:", height=150)

if st.button("Executar Análise"):
    if user_input:
        with st.spinner("Consultando algoritmos ICT..."):
            try:
                # O terminal usa o contexto técnico de cada tema selecionado
                contexto_tecnico = temas_originais[fluxo_selecionado]
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": f"Você é um especialista em ICT. Contexto atual: {contexto_tecnico}"},
                        {"role": "user", "content": user_input}
                    ],
                    model="llama3-8b-8192",
                )
                
                st.markdown(f"### 📝 Resultado para {fluxo_selecionado}:")
                st.write(chat_completion.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
    else:
        st.warning("Por favor, insira dados para análise.")

st.markdown("---")
st.caption("Terminal Online - Acesso Liberado via Smart Money Secrets")
