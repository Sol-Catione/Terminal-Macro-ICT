import streamlit as st
from groq import Groq
from gnews import GNews
import os

# 1. CONFIGURAÇÃO (primeira linha obrigatória)
st.set_page_config(
    page_title="Terminal ICT: Institutional Order Flow",
    layout="wide",
    page_icon="🏛️"
)

# 2. ESTADO SEGURO
if 'dados_terminal' not in st.session_state:
    st.session_state['dados_terminal'] = ""

# --- FUNÇÃO DE INTELIGÊNCIA (BLINDADA, MESMA LÓGICA) ---
def chamar_ia_groq(perfil, texto):
    try:
        # Chave da API
        if "GROQ_API_KEY" in st.secrets:
            key = st.secrets["GROQ_API_KEY"]
        else:
            return "⚠️ Erro: Chave API não configurada nos Secrets."

        client = Groq(api_key=key)

        messages = [
            {
                "role": "system",
                "content": f"Você é um {perfil} especializado em ICT. Responda em PORTUGUÊS técnico e direto."
            },
            {
                "role": "user",
                "content": f"Analise estes dados sob a ótica ICT:\n\n{texto[:3000]}"
            }
        ]

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            timeout=20  # 🔒 BLINDAGEM CONTRA TELA BRANCA
        )

        # 🔒 Proteção contra resposta vazia
        if not completion.choices:
            return "⚠️ A IA não retornou resposta."

        return completion.choices[0].message.content

    except Exception as e:
        return f"❌ Erro na consulta ({perfil}): {str(e)}"


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
        "🌍 Geopolítica & Macro": "Geopolitics global market news"
    }

    escolha = st.selectbox("Selecione o Fluxo:", list(temas_full.keys()))
    periodo = st.selectbox("Janela de Tempo:", ["12h", "24h", "48h", "7d", "30d"], index=3)

    if st.button("🌐 Sincronizar Sinais ICT"):
        with st.spinner("Buscando dados no servidor..."):
            try:
                gn = GNews(language='en', country='US', period=periodo, max_results=10)
                news = gn.get_news(temas_full[escolha])

                if news:
                    bruto = ""
                    for n in news:
                        bruto += f"FONTE: {n['publisher']['title']} | INFO: {n['title']}\n---\n"

                    st.session_state['dados_terminal'] = bruto
                    st.success("✅ Dados sincronizados!")
                else:
                    st.warning("Nenhum dado encontrado.")

            except Exception as e:
                st.error(f"Erro: {e}")

# --- CORPO PRINCIPAL ---
st.title("🏛️ Terminal ICT: Institutional Order Flow")
st.markdown("### Status: **Sistema Operacional** | Modelo: **Llama 3.1 Neural**")
st.write("Se você está vendo isso, o sistema carregou com sucesso!")
st.divider()

dados_atuais = st.session_state['dados_terminal']
noticias_campo = st.text_area(
    "Fluxo de Dados Capturado (Raw Data):",
    value=dados_atuais,
    height=150
)

# --- EXECUÇÃO DAS ANÁLISES ---
if st.button("🚀 Executar Análise Institucional"):
    if not noticias_campo or len(noticias_campo) < 10:
        st.error("⚠️ Erro: Sincronize os dados no menu lateral primeiro.")
    else:
        with st.status("🔍 Processando Viés Institucional...", expanded=True):

            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("🐋 Institutional Flow")
                res_smart = chamar_ia_groq(
                    'Especialista em Smart Money ICT',
                    noticias_campo
                )
                st.info(res_smart)

            with col2:
                st.subheader("🐟 Retail Trap")
                res_retail = chamar_ia_groq(
                    'Analista de Indução de Varejo',
                    noticias_campo
                )
                st.error(res_retail)

            with col3:
                st.subheader("🦅 Daily Bias")
                res_macro = chamar_ia_groq(
                    'Estrategista Macro',
                    noticias_campo
                )
                st.success(res_macro)

        st.divider()
        st.subheader("🎯 Plano de Execução Estratégica")

        # 🔒 BLINDAGEM DA ANÁLISE FINAL (CRÍTICA)
        try:
            res_final = chamar_ia_groq(
                'Gestor ICT Senior',
                f"Resumo Institucional:\n{res_smart}\n{res_macro}"
            )
            st.markdown(f"> {res_final}")
        except Exception as e:
            st.error(f"Erro na síntese final: {e}")

st.markdown("---")
st.caption("Terminal Macro ICT - V2.0 | Estabilidade Máxima")
