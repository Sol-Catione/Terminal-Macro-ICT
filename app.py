import streamlit as st
from groq import Groq
from gnews import GNews
import os

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Terminal ICT: Institutional Order Flow", layout="wide", page_icon="🏛️")

# --- FUNÇÃO DE INTELIGÊNCIA ---
def chamar_ia_groq(perfil, texto):
    try:
        if "GROQ_API_KEY" in st.secrets:
            key = st.secrets["GROQ_API_KEY"]
        elif os.environ.get("GROQ_API_KEY"):
            key = os.environ.get("GROQ_API_KEY")
        else:
            return "⚠️ Erro: Chave API não encontrada."
            
        client = Groq(api_key=key)
        modelo = "llama-3.1-8b-instant"

        messages = [
            {"role": "system", "content": f"""Você é um {perfil}. 
            Utilize estritamente a metodologia ICT (Inner Circle Trader). 
            Foque em: Liquidez (B-side/S-side), Fair Value Gaps (FVG), Order Blocks e Market Structure. 
            Responda em PORTUGUÊS técnico e direto."""},
            {"role": "user", "content": f"DADOS DE MERCADO:\n\n{texto[:3500]}"}
        ]

        completion = client.chat.completions.create(
            model=modelo,
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ Erro na IA: {str(e)}"

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Painel ICT & Macro")
    st.info("Acesso Institucional Liberado ✅")
    st.divider()

    temas_full = {
        "📊 COT & Institutional Bias": "Commitment of Traders CFTC smart money",
        "💱 Forex: ICT Majors": "DXY EURUSD price action analysis",
        "📀 Metais & Liquidez": "Gold Silver liquidity price action",
        "📈 Índices: S&P500 / Nasdaq (ICT)": "S&P500 Nasdaq price action",
        "🛢️ Commodities: ICT Flow": "Crude Oil market analysis",
        "🌍 Geopolítica & Macro": "Geopolitics global market news",
        "🏦 Política Monetária (Interest Rates)": "FED interest rates inflation news",
        "🕒 Killzones & High Impact": "Economic calendar high impact news"
    }

    escolha = st.selectbox("Selecione o Fluxo:", list(temas_full.keys()))
    periodo = st.selectbox("Janela de Tempo:", ["12h", "24h", "48h", "7d", "30d"], index=3)

    if st.button("🌐 Sincronizar Sinais ICT"):
        with st.spinner("Conectando às fontes elite..."):
            try:
                gn = GNews(language='en', country='US', period=periodo, max_results=10)
                news = gn.get_news(temas_full[escolha])
                
                if not news:
                    news = gn.get_news(escolha.split(':')[-1])

                if news:
                    bruto = ""
                    for n in news:
                        source = n['publisher']['title']
                        title = n['title']
                        bruto += f"FONTE: {source} | INFO: {title}\n---\n"
                    st.session_state['dados_terminal'] = bruto
                    st.success(f"✅ {len(news)} Sinais capturados!")
                    st.rerun()
                else:
                    st.warning("Nenhum sinal encontrado.")
            except Exception as e:
                st.error(f"Erro na sincronização: {e}")

# --- MENSAGEM DE BOAS-VINDAS ---
st.title("🏛️ Terminal ICT: Institutional Order Flow")
st.markdown(f"""
### Bem-vindo ao seu hub de Inteligência Algorítmica.
**Status:** Sistema Operacional | **Modelo:** Llama 3.1 Neural  
Análise de mercado sob a ótica do **Smart Money Concepts (SMC/ICT)**.
""")

st.divider()

# --- PAINEL PRINCIPAL ---
st.markdown(f"### 🎯 Análise Atual: **{escolha}**")

dados_atuais = st.session_state.get('dados_terminal', '')
noticias_campo = st.text_area("Fluxo de Dados Capturado (Raw Data):", value=dados_atuais, height=150)

if st.button("🚀 Executar Análise Institucional"):
    if noticias_campo:
        with st.spinner("Mapeando liquidez institucional..."):
            col1, col2, col3 = st.columns(3)
            
            res_smart = chamar_ia_groq('Especialista em ICT (Institutional Order Flow)', noticias_campo)
            res_retail = chamar_ia_groq('Analista de Indução e Liquidez de Varejo', noticias_campo)
            res_macro = chamar_ia_groq('Estrategista Macro e Daily Bias', noticias_campo)

            with col1: st.info(f"🐋 **Institutional Flow**\n\n{res_smart}")
            with col2: st.error(f"🐟 **Retail Trap**\n\n{res_retail}")
            with col3: st.success(f"🦅 **Daily Bias**\n\n{res_macro}")

            st.divider()
            st.subheader("🎯 Matriz de Execução Estratégica")
            
            ctx = f"Flow: {res_smart}\nTrap: {res_retail}\nBias: {res_macro}"
            veredito = chamar_ia_groq("Gestor ICT Senior", f"Gere um plano de trade curto com Bias, Liquidez e gatilho de entrada baseado nisso: {ctx}")
            st.markdown(f"> **PLANO FINAL DE EXECUÇÃO:**\n\n{veredito}")
    else:
        st.error("⚠️ Sincronize os dados primeiro.")

st.markdown("---")
st.caption("Terminal Macro ICT - V1.6 | Inteligência Institucional")
