from __future__ import annotations

import os
from typing import Any

import streamlit as st

import xau_asia_db
from llm_deepseek import deepseek_chat_completion
from groq import Groq
from xau_asia_ingest import read_asia_open_daily_csv
from xau_asia_oanda_build import build_xau_asia_open_daily_from_oanda
from xau_entry_heuristics import build_entry_plan
from oanda_candles import test_oanda_market_data_access


def _get_secret(name: str) -> str | None:
    try:
        if name in st.secrets:
            val = st.secrets[name]
            if isinstance(val, str) and val.strip():
                return val.strip()
    except Exception:
        pass
    val = os.environ.get(name)
    return val.strip() if isinstance(val, str) and val.strip() else None


def render_private_xau_asia_entry_agent() -> None:
    st.header("Gestao Privada")
    st.caption("Conteudo informativo/educacional. Nao e recomendacao de investimento.")

    conn = xau_asia_db.connect()
    stats = xau_asia_db.get_stats(conn)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Registros (Asia open)", stats.rows)
    with col_b:
        st.metric("Min date", stats.min_date or "-")
    with col_c:
        st.metric("Max date", stats.max_date or "-")

    st.divider()
    st.subheader("Base de dados (ultimos 3 anos)")
    st.write(
        "Opcao 1 (recomendado): baixar automaticamente do OANDA (XAU_USD) e gerar o snapshot das 02:00 Portugal "
        "com ATR14 por dia. Opcao 2: importar CSV."
    )

    with st.expander("OANDA: baixar e gerar base (02:00 Portugal)", expanded=True):
        oanda_key = _get_secret("OANDA_API_KEY")
        oanda_env = _get_secret("OANDA_ENV") or "practice"
        years = st.number_input("Anos de historico", min_value=1, max_value=10, value=3, step=1)
        granularity = st.selectbox("Granularity", options=["M5", "M1"], index=0)
        tz_name = "Europe/Lisbon"

        time_basis = st.radio(
            "Base de tempo para a abertura",
            options=["UTC (recomendado, sem DST)", "Portugal (Europe/Lisbon, pode variar em UTC)"],
            index=0,
            horizontal=True,
        )
        if time_basis.startswith("UTC"):
            anchor_mode = "utc"
            anchor_h = st.number_input("Horario (UTC) - hora", min_value=0, max_value=23, value=0, step=1)
            anchor_m = st.number_input("Horario (UTC) - minuto", min_value=0, max_value=59, value=0, step=1)
            st.caption("Recomendado para comparacao de padroes: sempre o mesmo timestamp em UTC (sem saltos de 1h).")
        else:
            anchor_mode = "local"
            anchor_h, anchor_m = 2, 0
            st.caption("Abertura fixada em 02:00 Portugal (Europe/Lisbon). Em horario de verao isso muda em UTC.")

        if not oanda_key:
            st.info("Configure `OANDA_API_KEY` e `OANDA_ENV` (practice/live) no secrets/env para habilitar o download.")
        else:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                test_clicked = st.button("Testar token OANDA")
            with col_t2:
                download_clicked = st.button("Baixar e atualizar base (OANDA:XAUUSD)")

            if test_clicked:
                with st.spinner("Testando acesso OANDA..."):
                    try:
                        msg = test_oanda_market_data_access(
                            api_key=oanda_key,
                            env=oanda_env,
                            instrument="XAU_USD",
                        )
                        if msg.startswith("OK"):
                            st.success(msg)
                        else:
                            st.warning(msg)
                    except Exception as e:
                        st.error(f"Falha ao testar token: {e}")

            if download_clicked:
                progress = st.progress(0, text="Inicializando...")

                def _cb(info: dict[str, Any]) -> None:
                    stage = info.get("stage")
                    if stage == "download":
                        # Not an exact %, but helps show liveness.
                        progress.progress(10, text=f"Baixando candles... ({info.get('candles')} lidos)")
                    elif stage == "build":
                        total = int(info.get("total_days") or 1)
                        done = int(info.get("days") or 0)
                        pct = 10 + int(80 * min(done / total, 1.0))
                        progress.progress(pct, text=f"Gerando dias (02:00 PT)... {done}/{total}")

                with st.spinner("Baixando candles do OANDA e calculando ATR..."):
                    try:
                        result = build_xau_asia_open_daily_from_oanda(
                            api_key=oanda_key,
                            env=oanda_env,
                            years=int(years),
                            instrument="XAU_USD",
                            granularity=str(granularity),
                            anchor_mode=anchor_mode,
                            anchor_time=(int(anchor_h), int(anchor_m)),
                            tz_name=tz_name,
                            progress_cb=_cb,
                        )
                        if not result.rows:
                            st.error("Nenhum dia gerado.")
                        else:
                            n = xau_asia_db.upsert_asia_open_daily(conn, result.rows)
                            progress.progress(100, text=f"Concluido. Dias importados/atualizados: {n}")
                            st.success(f"Concluido. Dias importados/atualizados: {n}")
                        for n in result.notes:
                            st.info(n)
                    except Exception as e:
                        st.error(f"OANDA: falha ao baixar/gerar base: {e}")
                stats = xau_asia_db.get_stats(conn)

    st.divider()
    st.subheader("Importar CSV (manual)")
    st.write("CSV minimo: `date` e `open` (opcional: `h1_high`, `h1_low`, `h1_close`, `atr14`).")
    uploaded = st.file_uploader("CSV (asia open daily)", type=["csv"])
    if uploaded is not None and st.button("Importar CSV"):
        rows, notes = read_asia_open_daily_csv(uploaded.getvalue(), source=uploaded.name)
        if not rows:
            st.error("Nenhuma linha valida para importar.")
        else:
            n = xau_asia_db.upsert_asia_open_daily(conn, rows)
            st.success(f"Importados/atualizados {n} dias.")
        for n in notes:
            st.info(n)

        # Refresh stats after import.
        stats = xau_asia_db.get_stats(conn)

    st.divider()
    st.subheader("Agente de entradas: XAU/USD (Abertura Asia)")

    with st.expander("Parametros", expanded=True):
        reference_price = st.number_input("Preco de referencia (XAU/USD)", min_value=0.0, value=2000.0, step=0.1)
        round_step = st.number_input("Numero redondo (step)", min_value=0.0, value=10.0, step=1.0)
        round_proximity = st.number_input("Proximidade do round (USD)", min_value=0.0, value=1.5, step=0.1)
        min_rr = st.number_input("RR minimo", min_value=1.0, value=1.0, step=0.1)

        st.write("Tesouraria (position sizing)")
        account_balance = st.number_input("Saldo (USD)", min_value=0.0, value=10000.0, step=100.0)
        risk_percent = st.number_input("Risco por trade (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.1)
        contract_size = st.number_input("Contract size (oz por lote)", min_value=1.0, value=100.0, step=1.0)

    history = xau_asia_db.fetch_last(conn, limit=1300)

    plan = build_entry_plan(
        history=history,
        reference_price=float(reference_price),
        round_step=float(round_step),
        round_proximity=float(round_proximity),
        min_rr=float(min_rr),
        account_balance=float(account_balance) if account_balance else None,
        risk_percent=float(risk_percent) if risk_percent else None,
        contract_size=float(contract_size),
    )

    st.markdown("**Sugestao (heuristica)**")
    out_col1, out_col2, out_col3, out_col4 = st.columns(4)
    out_col1.metric("Direcao", plan.direction)
    out_col2.metric("Entry", f"{plan.entry:.2f}")
    out_col3.metric("Stop", f"{plan.stop:.2f}")
    out_col4.metric("TP", f"{plan.take_profit:.2f}")

    st.write(f"RR efetivo: `{plan.rr:.2f}` | Stop distance: `{plan.stop_distance:.2f}`")
    if plan.lots is not None and plan.risk_amount is not None:
        st.write(f"Size (lotes): `{plan.lots:.4f}` | Risco (USD): `{plan.risk_amount:.2f}`")

    for n in plan.notes:
        st.caption(f"- {n}")

    st.divider()
    st.subheader("DeepSeek (opcional)")
    engine = st.radio(
        "Motor LLM",
        options=["DeepSeek (requer saldo)", "Groq (fallback)"],
        index=0,
        horizontal=True,
    )

    use_llm = st.toggle("Validar/refinar a entrada com LLM", value=False)
    if not use_llm:
        return

    system_prompt = (
        "Voce e um agente de entradas para XAUUSD focado na abertura da Asia. "
        "Responda de forma tecnica e direta. "
        "Nao de recomendacao financeira; apenas descreva um setup hipotetico e seus criterios."
    )
    user_prompt = (
        "Com base nas estatisticas e restricoes abaixo, proponha um setup (entry/stop/tp) "
        "com RR >= 1:1 e preferencia por numeros redondos.\n\n"
        f"Preco referencia: {reference_price}\n"
        f"Round step: {round_step}\n"
        f"Round proximity: {round_proximity}\n"
        f"Min RR: {min_rr}\n\n"
        f"Heuristica atual:\n"
        f"- Direcao: {plan.direction}\n"
        f"- Entry: {plan.entry:.2f}\n"
        f"- Stop: {plan.stop:.2f}\n"
        f"- TP: {plan.take_profit:.2f}\n"
        f"- RR: {plan.rr:.2f}\n\n"
        f"Stats:\n{plan.stats}\n\n"
        "Regras:\n"
        "- Se sugerir diferente, explique por que.\n"
        "- Use no maximo 8 linhas.\n"
    )

    if engine.startswith("DeepSeek"):
        api_key = _get_secret("DEEPSEEK_API_KEY")
        base_url = _get_secret("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1/chat/completions"
        model = _get_secret("DEEPSEEK_MODEL") or "deepseek-chat"

        if not api_key:
            st.error("Falta `DEEPSEEK_API_KEY` no secrets/env.")
            return

        with st.spinner("Consultando DeepSeek..."):
            try:
                resp = deepseek_chat_completion(
                    api_key=api_key,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    base_url=base_url,
                    timeout_s=20,
                    temperature=0.2,
                    max_tokens=700,
                )
                st.text(resp)
            except Exception as e:
                st.error(f"Falha ao chamar DeepSeek: {e}")
                st.info("Se quiser seguir sem pagar DeepSeek, mude o motor para `Groq (fallback)` acima.")
    else:
        groq_key = _get_secret("GROQ_API_KEY")
        if not groq_key:
            st.error("Falta `GROQ_API_KEY` no secrets/env.")
            return

        with st.spinner("Consultando Groq..."):
            try:
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=700,
                    timeout=20,
                )
                choices = completion.choices or []
                if not choices:
                    st.error("Groq: resposta vazia.")
                    return
                st.text(choices[0].message.content)
            except Exception as e:
                st.error(f"Falha ao chamar Groq: {e}")
