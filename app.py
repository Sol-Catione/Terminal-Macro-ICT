import streamlit as st
from groq import Groq
from gnews import GNews

# --- CONFIGURAÇÃO DA INTERFACE (ESTRUTURA FINAL SOLICITADA) ---
st.set_page_config(page_title="Terminal ICT: Institutional Order Flow", layout="wide", page_icon="🏛️")


# --- FUNÇÃO DE INTELIGÊNCIA ---
def chamar_ia_groq(perfil, texto, api_key):
    if not api_key: return "⚠️ Chave API ausente."
    try:
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
            max_tokens=1000  # Aumentado levemente para análise não cortar
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ Erro: {str(e)}"


# --- BARRA LATERAL (TODOS OS SEUS FLUXOS) ---
with st.sidebar:
    st.header("⚙️ Painel ICT & Macro")
    api_key = st.text_input("Chave API Groq:", type="password", help="Insira sua chave gsk_")

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
    periodo = st.selectbox("Janela de Tempo:", ["12h", "24h", "48h", "7d"], index=1)

    if st.button("🌐 Sincronizar Sinais ICT"):
        if not api_key:
            st.error("Insira a chave API primeiro.")
        else:
            with st.spinner("Mapeando liquidez algorítmica..."):
                gn = GNews(language='en', country='US', period=periodo, max_results=10)
                news = gn.get_news(temas_full[escolha])
                if news:
                    bruto = ""
                    for n in news:
                        bruto += f"FONTE: {n['publisher']['title']} | INFO: {n['title']}\n---\n"
                    st.session_state['dados_terminal'] = bruto
                    st.rerun()
                else:
                    st.error("Nenhum sinal encontrado.")

# --- PAINEL PRINCIPAL ---
st.title("🏛️ Terminal ICT: Institutional Order Flow")
st.markdown(f"### Estratégia ICT em: **{escolha}**")

# Garantindo que o campo de texto mantenha os dados
dados_atuais = st.session_state.get('dados_terminal', '')
noticias_campo = st.text_area("Fluxo de Dados Atual:", value=dados_atuais, height=150)

if st.button("🚀 Executar Análise Institucional"):
    if api_key and noticias_campo:
        with st.spinner("Identificando Order Blocks e FVG..."):
            col1, col2, col3 = st.columns(3)

            res_smart = chamar_ia_groq('Especialista em ICT (Institutional Order Flow)', noticias_campo, api_key)
            res_retail = chamar_ia_groq('Analista de Indução e Liquidez de Varejo', noticias_campo, api_key)
            res_macro = chamar_ia_groq('Estrategista Macro & ICT Bias', noticias_campo, api_key)

            with col1: st.info(f"🐋 **Institutional Flow (ICT)**\n\n{res_smart}")
            with col2: st.error(f"🐟 **Retail Trap (Liquidez de Sardinha)**\n\n{res_retail}")
            with col3: st.success(f"🦅 **Daily Bias (Direcionamento)**\n\n{res_macro}")

            st.divider()

            st.subheader("🎯 Matriz de Execução ICT")

            contexto_plano = f"Flow: {res_smart}\nTrap: {res_retail}\nBias: {res_macro}"
            prompt_plano = (
                "Com base na análise ICT:\n"
                "1. DAILY BIAS: (Alta ou Baixa e por quê).\n"
                "2. ZONAS DE LIQUIDEZ: (Onde as sardinhas deixaram Stops que serão capturados).\n"
                "3. PONTO DE INTERESSE (POI): (Order Blocks ou FVG importantes para entrada).\n"
                "4. GATILHO: (Aguardar MSS ou Judas Swing)."
            )

            veredito = chamar_ia_groq("Gestor ICT Senior", f"{prompt_plano}\n\nCONTEXTO: {contexto_plano}", api_key)
            st.markdown(f"> **PLANO DE EXECUÇÃO INSTITUCIONAL:**\n\n{veredito}")

    else:
        st.error("⚠️ Sincronize os dados e insira a Chave API.")
