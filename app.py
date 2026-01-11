import streamlit as st
from groq import Groq
from gnews import GNews

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Terminal ICT: Institutional Order Flow", layout="wide", page_icon="🏛️")

# --- FUNÇÃO DE INTELIGÊNCIA ---
def chamar_ia_groq(perfil, texto):
    try:
        if "GROQ_API_KEY" not in st.secrets:
            return "⚠️ Chave API não configurada no painel do Streamlit."
            
        key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=key)
        modelo = "llama-3.1-8b-instant"

        messages = [
            {"role": "system", "content": f"""Você é um {perfil}. 
            Utilize estritamente a metodologia ICT (Inner Circle Trader). 
            Foque em: Liquidez (B-side/S-side), Fair Value Gaps (FVG), Order Blocks, 
            Judas Swing, Market Structure Shift e Killzones. 
            Identifique onde o Smart Money está induzindo o varejo ao erro. 
            Responda em PORTUGUÊS técnico e direto."""},
            {"role": "user", "content": f"DADOS DE MERCADO (FONTES ELITE):\n\n{texto[:3500]}"}
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

    # Refinamento das buscas para as maiores fontes mundiais
    temas_full = {
        "📊 COT & Institutional Bias": "CFTC COT Report analysis Smart Money positioning Bloomberg Reuters",
        "💱 Forex: ICT Majors": "Forex DXY EURUSD analysis Reuters Bloomberg Investing.com",
        "📀 Metais & Liquidez": "Gold Silver price action liquidity analysis Reuters CNBC",
        "📈 Índices: S&P500 / Nasdaq (ICT)": "S&P500 Nasdaq price action Bloomberg Wall Street Journal",
        "🛢️ Commodities: ICT Flow": "Crude Oil Brent WTI market news Reuters Financial Times",
        "🌍 Geopolítica & Macro": "Global geopolitics trade wars analysis Bloomberg Reuters",
        "🏦 Política Monetária (Interest Rates)": "Central Banks FED FOMC interest rates Reuters Bloomberg FT",
        "🕒 Killzones & High Impact": "Economic calendar high impact news ForexFactory Bloomberg"
    }

    escolha = st.selectbox("Selecione o Fluxo:", list(temas_full.keys()))
    periodo = st.selectbox("Janela de Tempo:", ["12h", "24h", "48h", "7d"], index=3)

    if st.button("🌐 Sincronizar Sinais ICT"):
        with st.spinner("Conectando às 10 maiores fontes financeiras..."):
            try:
                # GNews configurado para buscar resultados de alta relevância (US/English são as fontes primárias ICT)
                gn = GNews(language='en', country='US', period=periodo, max_results=10)
                news = gn.get_news(temas_full[escolha])
                
                if news:
                    bruto = ""
                    for n in news:
                        source = n['publisher']['title']
                        title = n['title']
                        bruto += f"FONTE ELITE: {source} | INFO: {title}\n---\n"
                    st.session_state['dados_terminal'] = bruto
                    st.success(f"✅ {len(news)} Sinais de alta relevância capturados!")
                    st.rerun()
                else:
                    st.warning("Nenhum sinal encontrado. Tente aumentar para 7d.")
            except Exception as e:
                st.error(f"Erro na sincronização: {e}")

# --- PAINEL PRINCIPAL ---
st.title("🏛️ Terminal ICT: Institutional Order Flow")
st.markdown(f"### Estratégia ICT em: **{escolha}**")

dados_atuais = st.session_state.get('dados_terminal', '')
noticias_campo = st.text_area("Fluxo de Dados Atual (Top 10 Fontes):", value=dados_atuais, height=150)

if st.button("🚀 Executar Análise Institucional"):
    if noticias_campo:
        with st.spinner("Mapeando Order Flow e Liquidez..."):
            col1, col2, col3 = st.columns(3)
            res_smart = chamar_ia_groq('Especialista em ICT', noticias_campo)
            res_retail = chamar_ia_groq('Analista de Indução', noticias_campo)
            res_macro = chamar_ia_groq('Estrategista Macro', noticias_campo)

            with col1: st.info(f"🐋 **Institutional Flow**\n\n{res_smart}")
            with col2: st.error(f"🐟 **Retail Trap**\n\n{res_retail}")
            with col3: st.success(f"🦅 **Daily Bias**\n\n{res_macro}")

            st.divider()
            st.subheader("🎯 Plano de Execução")
            ctx = f"Flow: {res_smart}\nTrap: {res_retail}\nBias: {res_macro}"
            veredito = chamar_ia_groq("Gestor ICT Senior", f"Gere um plano curto com Bias, Liquidez e POI baseado nisso: {ctx}")
            st.markdown(f"> **PLANO FINAL:**\n\n{veredito}")
    else:
        st.error("⚠️ Sincronize os dados primeiro.")

st.markdown("---")
st.caption("Terminal Macro ICT - v1.2 | Data Sources: Top 10 Global Financial Outlets")
