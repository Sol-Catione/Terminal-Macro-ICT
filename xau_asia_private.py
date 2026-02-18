from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import trade_journal_db
from trade_pattern_analysis import extract_features, nearest_neighbors, summarize


def _parse_dt_lisbon_iso(s: str) -> datetime:
    # Stored as ISO with tz offset (Europe/Lisbon).
    v = (s or "").strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v).astimezone(ZoneInfo("Europe/Lisbon"))


@st.dialog("Print")
def _show_print_dialog(blob: bytes, caption: str) -> None:
    st.image(blob, caption=caption, use_container_width=True)


def render_private_xau_asia_entry_agent() -> None:
    st.header("Gestao Privada")
    st.caption("Objetivo: registrar entradas reais (prints) e extrair o operacional que se repete na Kill Zone Asia (23:00-03:00 PT).")

    conn = trade_journal_db.connect()
    st.metric("Trades cadastrados", trade_journal_db.count(conn))

    tab_add, tab_matrix, tab_list = st.tabs(["Cadastrar", "Matriz", "Registros"])

    with tab_add:
        st.subheader("Cadastrar Trade (Manual + Print)")
        st.write("Preencha os dados do trade e anexe o print. O sistema usa ATR e numeração psicológica para achar repetição.")

        with st.form("trade_add_form", clear_on_submit=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                trade_id = st.text_input("Trade ID (unico)", placeholder="ex: 2026-02-18_0115_PT_LONG")
                symbol = st.text_input("Symbol", value="XAUUSD")
                direction = st.selectbox("Direcao", options=["LONG", "SHORT"])
            with col2:
                timeframe_min = st.number_input("Timeframe (min)", min_value=1, max_value=240, value=15, step=1)
                dt_date = st.date_input("Data (Portugal)", value=None)
                dt_time = st.time_input("Hora (Portugal)", value=None)
            with col3:
                entry = st.number_input("Entry", min_value=0.0, value=0.0, step=0.01)
                sl = st.number_input("SL", min_value=0.0, value=0.0, step=0.01)
                tp = st.number_input("TP", min_value=0.0, value=0.0, step=0.01)

            st.write("Numeração psicológica (opcional, recomendado)")
            col_ps1, col_ps2, col_ps3 = st.columns(3)
            with col_ps1:
                psych_step = st.number_input("Step psicológico (USD)", min_value=0.0, value=10.0, step=1.0)
                level_type = st.selectbox("Tipo do nível", options=["", "SUPORTE", "RESISTENCIA"], index=0)
            with col_ps2:
                psych_level = st.number_input("Nível testado (ex: 5000)", min_value=0.0, value=0.0, step=1.0)
                touched_level = st.checkbox("Tocou o nível", value=False)
            with col_ps3:
                rejection = st.checkbox("Rejeição (pavio/fechamento)", value=False)
                confirmation = st.checkbox("Confirmação no candle seguinte", value=False)

            col4, col5 = st.columns(2)
            with col4:
                atr14 = st.number_input("ATR(14) no candle de entrada", min_value=0.0, value=0.0, step=0.01)
            with col5:
                result_r = st.number_input("Resultado (em R)", value=0.0, step=0.01, help="Ex: +1.00, -1.00, +0.92")

            image = st.file_uploader("Anexar print (opcional)", type=["png", "jpg", "jpeg", "webp"])
            notes = st.text_area("Notas", placeholder="Ex: contexto, confluencias, etc.")

            submitted = st.form_submit_button("Salvar trade")

        if image is not None:
            st.image(image, caption=image.name, width=260)

        if submitted:
            if not trade_id.strip():
                st.error("Trade ID e obrigatorio.")
            elif dt_date is None or dt_time is None:
                st.error("Data e hora (Portugal) sao obrigatorias.")
            elif entry <= 0 or sl <= 0 or tp <= 0:
                st.error("Entry/SL/TP precisam ser > 0.")
            else:
                tz = ZoneInfo("Europe/Lisbon")
                dt_local = datetime.combine(dt_date, dt_time).replace(tzinfo=tz)
                dt_utc = dt_local.astimezone(ZoneInfo("UTC"))

                row = {
                    "trade_id": trade_id.strip(),
                    "symbol": symbol.strip() or "XAUUSD",
                    "timeframe_min": int(timeframe_min),
                    "dt_lisbon": dt_local.isoformat(),
                    "dt_utc": dt_utc.isoformat().replace("+00:00", "Z"),
                    "direction": direction,
                    "psych_step": float(psych_step) if psych_step and psych_step > 0 else None,
                    "psych_level": float(psych_level) if psych_level and psych_level > 0 else None,
                    "level_type": level_type if level_type else None,
                    "touched_level": 1 if touched_level else 0,
                    "rejection": 1 if rejection else 0,
                    "confirmation": 1 if confirmation else 0,
                    "entry": float(entry),
                    "sl": float(sl),
                    "tp": float(tp),
                    "atr14": float(atr14) if atr14 and atr14 > 0 else None,
                    "result_r": float(result_r),
                    "notes": notes.strip() if notes.strip() else None,
                    "image_name": image.name if image is not None else None,
                    "image_mime": image.type if image is not None else None,
                    "image_blob": image.getvalue() if image is not None else None,
                }
                trade_journal_db.upsert_trade_samples(conn, [row])
                st.success("Trade salvo.")

    with tab_matrix:
        st.subheader("Agente: Matriz de Comparacao de Entradas")
        st.write(
            "A matriz compara trades por assinatura (hora, timeframe, direcao) e por volatilidade (ATR), "
            "alem de numeração psicológica quando preenchida."
        )

        trades = trade_journal_db.fetch_all(conn)
        if not trades:
            st.info("Cadastre trades na aba `Cadastrar` para habilitar a matriz.")
        else:
            colf1, colf2 = st.columns(2)
            with colf1:
                only_asia = st.toggle("Filtrar Kill Zone Asia (23:00-03:00 PT)", value=True)
            with colf2:
                default_step = st.number_input("Step default (USD)", min_value=0.0, value=10.0, step=1.0)

            feats = extract_features(trades, default_round_step=float(default_step))
            if only_asia:
                feats = [f for f in feats if (f.hour >= 23 or f.hour <= 3)]

            st.write(summarize(feats))

            ids = [f.trade_id for f in feats]
            if not ids:
                st.info("Nenhum trade ficou dentro do filtro atual.")
            else:
                colm1, colm2 = st.columns(2)
                with colm1:
                    target_id = st.selectbox("Trade alvo", options=ids, index=max(0, len(ids) - 1))
                with colm2:
                    k = st.number_input("Top K similares", min_value=1, max_value=25, value=8, step=1)

                nn = nearest_neighbors(feats, target_id=target_id, k=int(k))

                blob, _, name = trade_journal_db.fetch_image(conn, target_id)
                if blob:
                    st.image(blob, caption=name or target_id, width=260)
                    if st.button("Abrir print", key=f"open_print_matrix_{target_id}"):
                        _show_print_dialog(blob, name or target_id)

                if nn:
                    st.write("Mais parecidos (distancia menor = mais parecido):")
                    st.table([{"trade_id": tid, "distance": round(d, 4)} for tid, d in nn])
                else:
                    st.info("Nao foi possivel achar vizinhos para o trade alvo.")

    with tab_list:
        st.subheader("Registros (Tabela)")
        trades = trade_journal_db.fetch_all(conn)
        if not trades:
            st.info("Nenhum trade cadastrado ainda.")
        else:
            rows = []
            for t in trades:
                rows.append(
                    {
                        "trade_id": t.trade_id,
                        "dt_lisbon": t.dt_lisbon,
                        "symbol": t.symbol,
                        "tf_min": t.timeframe_min,
                        "dir": t.direction,
                        "entry": t.entry,
                        "sl": t.sl,
                        "tp": t.tp,
                        "atr14": t.atr14,
                        "result_r": t.result_r,
                        "psych_step": t.psych_step,
                        "psych_level": t.psych_level,
                        "level_type": t.level_type,
                        "touched": t.touched_level,
                        "rejection": t.rejection,
                        "confirm": t.confirmation,
                        "has_img": t.has_image,
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("Editar Registro")
            st.caption("Edicao sobrescreve os campos do trade selecionado. Para trocar/remover o print, use os botoes abaixo.")

            trade_ids = [t.trade_id for t in trades]
            edit_id = st.selectbox("Trade ID", options=trade_ids, index=len(trade_ids) - 1)
            current = next((t for t in trades if t.trade_id == edit_id), None)
            if current is None:
                st.error("Trade nao encontrado.")
                return

            blob, _, name = trade_journal_db.fetch_image(conn, edit_id)
            if blob:
                st.image(blob, caption=name or edit_id, width=260)
                if st.button("Abrir print", key=f"open_print_edit_{edit_id}"):
                    _show_print_dialog(blob, name or edit_id)

            dt_local = _parse_dt_lisbon_iso(current.dt_lisbon)

            with st.form("trade_edit_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    symbol = st.text_input("Symbol", value=current.symbol)
                    direction = st.selectbox(
                        "Direcao",
                        options=["LONG", "SHORT"],
                        index=0 if current.direction.upper() == "LONG" else 1,
                    )
                    timeframe_min = st.number_input(
                        "Timeframe (min)",
                        min_value=1,
                        max_value=240,
                        value=int(current.timeframe_min),
                        step=1,
                    )
                with col2:
                    dt_date = st.date_input("Data (Portugal)", value=dt_local.date())
                    dt_time = st.time_input("Hora (Portugal)", value=dt_local.time().replace(microsecond=0))
                    atr14 = st.number_input(
                        "ATR(14) no candle de entrada",
                        min_value=0.0,
                        value=float(current.atr14) if current.atr14 is not None else 0.0,
                        step=0.01,
                    )
                with col3:
                    entry = st.number_input("Entry", min_value=0.0, value=float(current.entry), step=0.01)
                    sl = st.number_input("SL", min_value=0.0, value=float(current.sl), step=0.01)
                    tp = st.number_input("TP", min_value=0.0, value=float(current.tp), step=0.01)

                st.write("Numeração psicológica")
                colp1, colp2, colp3 = st.columns(3)
                with colp1:
                    psych_step = st.number_input(
                        "Step psicológico (USD)",
                        min_value=0.0,
                        value=float(current.psych_step) if current.psych_step is not None else 10.0,
                        step=1.0,
                    )
                    level_type = st.selectbox(
                        "Tipo do nível",
                        options=["", "SUPORTE", "RESISTENCIA"],
                        index=(
                            1
                            if (current.level_type or "").upper() == "SUPORTE"
                            else 2
                            if (current.level_type or "").upper() == "RESISTENCIA"
                            else 0
                        ),
                    )
                with colp2:
                    psych_level = st.number_input(
                        "Nível testado (ex: 5000)",
                        min_value=0.0,
                        value=float(current.psych_level) if current.psych_level is not None else 0.0,
                        step=1.0,
                    )
                    touched_level = st.checkbox("Tocou o nível", value=bool(current.touched_level))
                with colp3:
                    rejection = st.checkbox("Rejeição", value=bool(current.rejection))
                    confirmation = st.checkbox("Confirmação", value=bool(current.confirmation))

                result_r = st.number_input(
                    "Resultado (em R)",
                    value=float(current.result_r) if current.result_r is not None else 0.0,
                    step=0.01,
                )
                notes = st.text_area("Notas", value=current.notes or "")

                replace_img = st.file_uploader(
                    "Trocar print (opcional)",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"replace_img_{edit_id}",
                )
                save = st.form_submit_button("Salvar alteracoes")

            colb1, colb2 = st.columns(2)
            with colb1:
                if blob and st.button("Remover print"):
                    trade_journal_db.update_image(conn, edit_id, image_blob=None, image_mime=None, image_name=None)
                    st.success("Print removido.")
            with colb2:
                confirm_delete = st.checkbox("Confirmar exclusao", value=False)
                if st.button("Apagar trade") and confirm_delete:
                    trade_journal_db.delete_trade(conn, edit_id)
                    st.success("Trade apagado.")

            if save:
                if entry <= 0 or sl <= 0 or tp <= 0:
                    st.error("Entry/SL/TP precisam ser > 0.")
                else:
                    tz = ZoneInfo("Europe/Lisbon")
                    dt_new_local = datetime.combine(dt_date, dt_time).replace(tzinfo=tz)
                    dt_new_utc = dt_new_local.astimezone(ZoneInfo("UTC"))

                    row = {
                        "trade_id": edit_id,
                        "symbol": symbol.strip() or "XAUUSD",
                        "timeframe_min": int(timeframe_min),
                        "dt_lisbon": dt_new_local.isoformat(),
                        "dt_utc": dt_new_utc.isoformat().replace("+00:00", "Z"),
                        "direction": direction,
                        "psych_step": float(psych_step) if psych_step and psych_step > 0 else None,
                        "psych_level": float(psych_level) if psych_level and psych_level > 0 else None,
                        "level_type": level_type if level_type else None,
                        "touched_level": 1 if touched_level else 0,
                        "rejection": 1 if rejection else 0,
                        "confirmation": 1 if confirmation else 0,
                        "entry": float(entry),
                        "sl": float(sl),
                        "tp": float(tp),
                        "atr14": float(atr14) if atr14 and atr14 > 0 else None,
                        "result_r": float(result_r),
                        "notes": notes.strip() if notes.strip() else None,
                        "image_name": replace_img.name if replace_img is not None else None,
                        "image_mime": replace_img.type if replace_img is not None else None,
                        "image_blob": replace_img.getvalue() if replace_img is not None else None,
                    }
                    trade_journal_db.upsert_trade_samples(conn, [row])
                    st.success("Alteracoes salvas.")
