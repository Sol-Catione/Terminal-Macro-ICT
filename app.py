import hmac
import os

import streamlit as st
from gnews import GNews
from groq import Groq

from xau_asia_private import render_private_xau_asia_entry_agent


st.set_page_config(
    page_title="Terminal ICT: Institutional Order Flow",
    layout="wide",
)


if "dados_terminal" not in st.session_state:
    st.session_state["dados_terminal"] = ""
if "private_unlocked" not in st.session_state:
    st.session_state["private_unlocked"] = False


def _get_secret(name: str) -> str | None:
    # Prefer Streamlit secrets, fallback to environment variables.
    try:
        if name in st.secrets:
            val = st.secrets[name]
            if isinstance(val, str) and val.strip():
                return val.strip()
    except Exception:
        pass

    val = os.environ.get(name)
    return val.strip() if isinstance(val, str) and val.strip() else None


def _render_private_unlock_sidebar() -> None:
    st.sidebar.divider()
    st.sidebar.subheader("Private")

    if st.session_state.get("private_unlocked"):
        st.sidebar.success("Unlocked")
        if st.sidebar.button("Logout"):
            st.session_state["private_unlocked"] = False
        return

    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Unlock"):
        expected = _get_secret("PRIVATE_PASSWORD")
        if not expected:
            st.sidebar.error("Missing PRIVATE_PASSWORD in secrets/env.")
            return
        if hmac.compare_digest(password or "", expected):
            st.session_state["private_unlocked"] = True
            st.sidebar.success("Unlocked")
        else:
            st.sidebar.error("Invalid password.")


def chamar_ia_groq(perfil: str, texto: str) -> str:
    try:
        key = _get_secret("GROQ_API_KEY")
        if not key:
            return "Erro: GROQ_API_KEY nao configurada (secrets/env)."

        client = Groq(api_key=key)
        messages = [
            {
                "role": "system",
                "content": f"Voce e um {perfil} especializado em ICT. Responda em PORTUGUES tecnico e direto.",
            },
            {"role": "user", "content": f"Analise estes dados sob a otica ICT:\n\n{texto[:3000]}"},
        ]

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3,
            max_tokens=800,
            timeout=20,
        )
        if not completion.choices:
            return "A IA nao retornou resposta."
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erro na consulta ({perfil}): {str(e)}"


with st.sidebar:
    st.header("Painel ICT & Macro")
    st.info("Acesso institucional liberado")
    st.divider()

    temas_full = {
        "COT & Institutional Bias": "Commitment of Traders CFTC smart money",
        "Forex: ICT Majors": "DXY EURUSD price action analysis",
        "Metais & Liquidez": "Gold Silver liquidity price action",
        "Indices: S&P500 / Nasdaq (ICT)": "S&P500 Nasdaq price action",
        "Geopolitica & Macro": "Geopolitics global market news",
    }

    escolha = st.selectbox("Selecione o fluxo:", list(temas_full.keys()))
    periodo = st.selectbox("Janela de tempo:", ["12h", "24h", "48h", "7d", "30d"], index=3)

    if st.button("Sincronizar sinais ICT"):
        with st.spinner("Buscando dados..."):
            try:
                gn = GNews(language="en", country="US", period=periodo, max_results=10)
                news = gn.get_news(temas_full[escolha])

                if news:
                    bruto = ""
                    for n in news:
                        bruto += f"FONTE: {n['publisher']['title']} | INFO: {n['title']}\n---\n"
                    st.session_state["dados_terminal"] = bruto
                    st.success("Dados sincronizados.")
                else:
                    st.warning("Nenhum dado encontrado.")
            except Exception as e:
                st.error(f"Erro: {e}")

    _render_private_unlock_sidebar()


tab_public, tab_private = st.tabs(["Terminal ICT", "Gestao privada"])

with tab_public:
    st.title("Terminal ICT: Institutional Order Flow")
    st.markdown("### Status: Sistema operacional | Modelo: Llama 3.1 (Groq)")
    st.divider()

    noticias_campo = st.text_area(
        "Fluxo de dados capturado (raw):",
        value=st.session_state["dados_terminal"],
        height=150,
    )

    if st.button("Executar analise institucional"):
        if not noticias_campo or len(noticias_campo) < 10:
            st.error("Sincronize os dados no menu lateral primeiro.")
        else:
            with st.status("Processando vies institucional...", expanded=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.subheader("Institutional Flow")
                    res_smart = chamar_ia_groq("Especialista em Smart Money ICT", noticias_campo)
                    st.info(res_smart)

                with col2:
                    st.subheader("Retail Trap")
                    res_retail = chamar_ia_groq("Analista de Inducao de Varejo", noticias_campo)
                    st.error(res_retail)

                with col3:
                    st.subheader("Daily Bias")
                    res_macro = chamar_ia_groq("Estrategista Macro", noticias_campo)
                    st.success(res_macro)

            st.divider()
            st.subheader("Plano de execucao estrategica")
            try:
                res_final = chamar_ia_groq(
                    "Gestor ICT Senior", f"Resumo institucional:\n{res_smart}\n{res_macro}"
                )
                st.markdown(f"> {res_final}")
            except Exception as e:
                st.error(f"Erro na sintese final: {e}")

with tab_private:
    if not st.session_state.get("private_unlocked"):
        st.warning("Area privada bloqueada. Desbloqueie no menu lateral (Private -> Unlock).")
    else:
        render_private_xau_asia_entry_agent()

st.markdown("---")
st.caption("Terminal Macro ICT - V2.1 | Area privada + agentes")
