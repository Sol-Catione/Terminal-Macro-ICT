import streamlit as st
from groq import Groq
from gnews import GNews

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira coisa no código)
st.set_page_config(page_title="Terminal Macro ICT", page_icon="📈", layout="wide")

# 2. ACESSO SEGURO À CHAVE API
# O código vai buscar a chave que você salvou nos 'Secrets' do Streamlit
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("⚠️ Erro: Chave API não configurada nos Secrets do Streamlit.")
    st.stop()

# 3. INTERFACE DO USUÁRIO
st.title("📟 Terminal Macro - Estratégia ICT")
st.markdown("---")

# Menu de Seleção de Fluxo
fluxo = st.selectbox(
    "Escolha o Fluxo de Análise:",
    [
        "1. Fluxo de Continuidade",
        "2. Fluxo de Reversão",
        "3. Fluxo de Expansão",
        "4. Fluxo de Consolidação",
        "5. Fluxo de Manipulação (Judas Swing)",
        "6. Fluxo de Notícias Macro",
        "7. Fluxo de Correlação (Smt Divergence)"
    ]
)

# 4. DEFINIÇÃO DOS CONTEXTOS (Os seus 7 temas)
contextos = {
    "1. Fluxo de Continuidade": "Você é um mentor de trading ICT. Explique o fluxo de continuidade focado em Order Block e Fair Value Gaps...",
    "2. Fluxo de Reversão": "Você é um mentor de trading ICT. Explique como identificar uma reversão após a quebra de estrutura (MSS)...",
    "3. Fluxo de Expansão": "Explique o conceito de expansão e como identificar o range de negociação...",
    "4. Fluxo de Consolidação": "Explique o comportamento do preço em consolidação e como evitar falsos rompimentos...",
    "5. Fluxo de Manipulação (Judas Swing)": "Explique o Judas Swing na abertura de Londres ou Nova York...",
    "6. Fluxo de Notícias Macro": "Analise o impacto das notícias de alto impacto (NFP, CPI) no viés diário...",
    "7. Fluxo de Correlação (Smt Divergence)": "Explique como a divergência SMT entre pares correlacionados (ex: EURUSD e GBPUSD) confirma entradas..."
}

# 5. ÁREA DE CHAT
st.subheader(f"Análise: {fluxo}")

user_input = st.text_input("Digite sua dúvida ou o par de moedas para análise:")

if st.button("Executar Análise"):
    if user_input:
        with st.spinner("O Terminal está processando os dados..."):
            try:
                # Chama a IA usando o contexto do fluxo escolhido
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": contextos[fluxo]},
                        {"role": "user", "content": user_input}
                    ],
                    model="llama3-8b-8192",
                )
                
                resposta = chat_completion.choices[0].message.content
                st.markdown("### 📝 Resposta do Terminal:")
                st.write(resposta)
                
            except Exception as e:
                st.error(f"Ocorreu um erro na comunicação com a IA: {e}")
    else:
        st.warning("Por favor, digite algo para o terminal analisar.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido por Sol Catione | Terminal Macro ICT v1.0")
