import streamlit as st
from groq import Groq
from gnews import GNews

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Terminal ICT: Institutional Order Flow", layout="wide", page_icon="🏛️")

# --- FUNÇÃO DE INTELIGÊNCIA (USANDO SECRETS) ---
def chamar_ia_groq(perfil, texto):
    try:
        # Pega a chave automaticamente dos Secrets do Streamlit
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
        modelo = "llama-3.1-8b-instant"

        messages = [
            {"role": "system", "content": f"""Você é um {perfil}. 
            Utilize estritamente a metodologia ICT (Inner Circle Trader). 
            Foque em: Liquidez (B-side/S-side), Fair Value Gaps (FVG), Order Blocks, 
            Judas Swing, Market Structure Shift e Killzones. 
            Identifique onde o Smart Money está induzindo o varejo ao erro. 
            Responda em PORTUGUÊS técnico."""},
            {"role": "user", "content": f"DADOS DE MERCADO:\n\n{texto[:3000]}"}
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

# --- BARRA LATERAL (PAINEL DE CONTROLE) ---
with st.sidebar:
    st.header("⚙️ Painel ICT & Macro")
    st.info("Acesso Institucional Liberado ✅")

    st.divider()

    temas_full = {
        "📊 COT & Institutional Bias": "COT report institutional net positions Smart Money",
        "💱 Forex: ICT Majors": "DXY EURUSD USDJPY algorithmic price action",
        "📀 Metais & Liquidez": "gold silver liquidity pools silver bullet",
        "📈 Índices: S&P500 / Nasdaq (ICT)": "S&P500 Nasdaq ES NQ price action liquidity",
        "🛢️ Commodities: ICT Flow": "crude oil brent wti order flow institutional",
        "🌍 Geopolítica & Macro": "geopolitics global conflict trade wars",
        "🏦 Política Monetária (Interest Rates)": "central banks FED inflation interest rates",
        "🕒 Killzones & High Impact": "economic calendar NFP FOMC news volatility"
    }

    escolha = st.selectbox("Selecione o Fluxo:", list(temas_full.keys()))
    # Sugestão: Use '7d' se quiser garantir que sempre apareçam notícias
    periodo = st.selectbox("Janela de Tempo:", ["12h", "24h", "48h", "7d"], index=3)

    if st.button("🌐 Sincronizar Sinais ICT"):
        with st.spinner("Mapeando liquidez algorítmica..."):
            try:
                gn = GNews(language='en', country='US', period=periodo, max_results=10)
                news = gn.get_news(temas_full[escolha])
                
                if news:
                    bruto = ""
                    for n in news:
                        bruto += f"FONTE: {n['publisher']['title']} | INFO: {n['title']}\n---\n"
                    st.session_state['dados_terminal'] = bruto
                    st.success(f"✅ {len(news)} notícias sincronizadas!")
                    st.rerun()
                else:
                    st.warning("Nenhum sinal encontrado. Tente aumentar a 'Janela de Tempo' para 7d.")
            except Exception as e:
                st.error(f"Erro na sincronização: {e}")

# --- PAINEL PRINCIPAL (INTERFACE DO TERMINAL) ---
st.title("🏛️ Terminal ICT: Institutional Order Flow")
st.markdown(f"### Estratégia ICT em: **{escolha}**")

# Campo de dados (onde as notícias aparecem)
dados_atuais = st.session_state.get('dados_terminal', '')
noticias_campo = st.text_area("Fluxo de Dados Atual:", value=dados_atuais, height=150)

if st.button("🚀 Executar Análise Institucional"):
    if noticias_campo:
        with st.spinner("Identificando Order Blocks e FVG..."):
            col1, col2, col3 = st.columns(3)

            # Executa as 3 análises simultâneas
            res_smart = chamar_ia_groq('Especialista em ICT (Institutional Order Flow)', noticias_campo)
            res_retail = chamar_ia_groq('Analista de Indução e Liquidez de Varejo', noticias_campo)
            res_macro = chamar_ia_groq('Estrategista Macro & ICT Bias', noticias_campo)

            with col1: st.info(f"🐋 **Institutional Flow (ICT)**\n\n{res_smart}")
            with col
