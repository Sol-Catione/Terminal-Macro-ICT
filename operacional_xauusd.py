from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Any

from zoneinfo import ZoneInfo


class Direcao(Enum):
    COMPRA = "BUY"
    VENDA = "SELL"
    NEUTRO = "NEUTRAL"


@dataclass(frozen=True)
class JanelaPrioritaria:
    inicio: time
    fim: time
    direcao_esperada: str  # "VENDA" | "COMPRA" | "AMBAS"


@dataclass(frozen=True)
class ConfiguracaoOperacional:
    # Kill Zone Asiática (Portugal / Europe/Lisbon). Janela atravessa meia-noite.
    kill_zone_inicio: time = time(23, 0)
    kill_zone_fim: time = time(6, 0)

    # Janelas prioritarias (comportamento esperado).
    janelas_prioritarias: tuple[JanelaPrioritaria, ...] = (
        JanelaPrioritaria(inicio=time(23, 20), fim=time(0, 30), direcao_esperada="VENDA"),
        JanelaPrioritaria(inicio=time(0, 30), fim=time(1, 30), direcao_esperada="AMBAS"),
        JanelaPrioritaria(inicio=time(3, 0), fim=time(4, 0), direcao_esperada="COMPRA"),
        JanelaPrioritaria(inicio=time(5, 0), fim=time(6, 0), direcao_esperada="VENDA"),
    )

    # Limite de operacoes por janela
    max_operacoes_por_janela: int = 2

    # Stops estruturais (mesma unidade do preco do feed)
    stop_minimo: float = 35.0
    stop_maximo: float = 65.0
    stop_apertado_limite: float = 10.0

    # Alvos
    numero_alvos: int = 4

    # Rejeicao
    tamanho_min_pavio: float = 2.0
    toque_tolerancia: float = 0.5
    forca_rejeicao_min: float = 1.5

    # Stats (informativo)
    assertividade_esperada: float = 0.87


@dataclass(frozen=True)
class NivelPsicologico:
    valor: float
    step: float
    tipo: str  # "suporte", "resistencia", "ambos"
    forca: int  # 1-5


class AnalisadorNiveisPsicologicos:
    def identificar_step_do_dia(self, preco_atual: float) -> float:
        if preco_atual < 4800:
            return 50.0
        if preco_atual < 5000:
            return 10.0
        return 20.0

    def calcular_forca_nivel(self, nivel: float) -> int:
        if nivel % 100 == 0:
            return 5
        if nivel % 50 == 0:
            return 4
        if nivel % 20 == 0:
            return 3
        if nivel % 10 == 0:
            return 2
        return 1

    def identificar_tipo_nivel(self, nivel: float, preco_atual: float) -> str:
        if nivel < preco_atual:
            return "suporte"
        if nivel > preco_atual:
            return "resistencia"
        return "ambos"

    def get_niveis_psicologicos(self, preco_atual: float, step_dia: float | None = None) -> list[NivelPsicologico]:
        step_dia = float(step_dia) if step_dia and step_dia > 0 else self.identificar_step_do_dia(preco_atual)
        base = round(preco_atual / step_dia) * step_dia

        niveis: list[NivelPsicologico] = []
        for offset_steps in range(-40, 41):
            nivel_valor = base + offset_steps * step_dia
            if nivel_valor <= 0:
                continue
            nivel_valor = float(nivel_valor)
            niveis.append(
                NivelPsicologico(
                    valor=nivel_valor,
                    step=float(step_dia),
                    tipo=self.identificar_tipo_nivel(nivel_valor, preco_atual),
                    forca=self.calcular_forca_nivel(nivel_valor),
                )
            )

        niveis.sort(key=lambda x: abs(x.valor - preco_atual))
        return niveis[:20]


class DetectorRejeicao:
    def __init__(self, tamanho_min_pavio: float, toque_tolerancia: float):
        self.tamanho_min_pavio = float(tamanho_min_pavio)
        self.toque_tolerancia = float(toque_tolerancia)

    def detectar_rejeicao(self, candle: dict[str, float], nivel: float, direcao_esperada: str) -> tuple[bool, float]:
        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])

        pavio_superior = h - max(c, o)
        pavio_inferior = min(c, o) - l

        if direcao_esperada == "COMPRA":
            tocou = l <= (nivel + self.toque_tolerancia)
            if tocou and pavio_inferior >= self.tamanho_min_pavio:
                forca = min(pavio_inferior / self.tamanho_min_pavio, 3.0)
                return True, float(forca)

        if direcao_esperada == "VENDA":
            tocou = h >= (nivel - self.toque_tolerancia)
            if tocou and pavio_superior >= self.tamanho_min_pavio:
                forca = min(pavio_superior / self.tamanho_min_pavio, 3.0)
                return True, float(forca)

        return False, 0.0


class CalculadorStopEstrutural:
    @staticmethod
    def calcular_stop(direcao: Direcao, nivel_testado: float, contexto: dict[str, Any], stop_min: float) -> float:
        if direcao == Direcao.COMPRA:
            minima = float(contexto.get("minima_recente", nivel_testado - stop_min))
            stop = min(minima - 2.0, nivel_testado - stop_min)
        else:
            maxima = float(contexto.get("maxima_recente", nivel_testado + stop_min))
            stop = max(maxima + 2.0, nivel_testado + stop_min)
        return round(float(stop), 2)

    @staticmethod
    def risco_pontos(entrada: float, stop: float) -> float:
        return abs(float(entrada) - float(stop))


class GeradorAlvos:
    def __init__(self, num_alvos: int):
        self.num_alvos = int(num_alvos)

    def gerar_alvos(self, entrada: float, direcao: Direcao, step_dia: float) -> list[float]:
        step_dia = float(step_dia)
        base = round(float(entrada) / step_dia) * step_dia
        alvos: list[float] = []

        if direcao == Direcao.COMPRA:
            for i in range(1, self.num_alvos + 1):
                alvo = base + i * step_dia
                if alvo > entrada:
                    alvos.append(round(float(alvo), 2))
        else:
            for i in range(1, self.num_alvos + 1):
                alvo = base - i * step_dia
                if alvo < entrada:
                    alvos.append(round(float(alvo), 2))

        return alvos[: self.num_alvos]


@dataclass(frozen=True)
class SinalOperacional:
    direcao: Direcao
    entrada: float
    stop: float
    alvos: list[float]
    nivel_testado: float
    forca_rejeicao: float
    risco_pontos: float
    janela: str
    timestamp: datetime


def _time_in_window(t: time, start: time, end: time) -> bool:
    # Window may cross midnight.
    if start <= end:
        return start <= t <= end
    return t >= start or t <= end


class OperacionalKillZone:
    """
    Motor de regras do operacional (Kill Zone Asiática).
    Nao e recomendacao financeira.
    """

    def __init__(self, config: ConfiguracaoOperacional | None = None):
        self.config = config or ConfiguracaoOperacional()
        self.analisador_niveis = AnalisadorNiveisPsicologicos()
        self.detector_rejeicao = DetectorRejeicao(
            tamanho_min_pavio=self.config.tamanho_min_pavio,
            toque_tolerancia=self.config.toque_tolerancia,
        )
        self.gerador_alvos = GeradorAlvos(self.config.numero_alvos)

        self._day_key: date | None = None
        self._ops_by_window: dict[str, int] = {}

    def _reset_if_new_day(self, day_key: date) -> None:
        if self._day_key != day_key:
            self._day_key = day_key
            self._ops_by_window = {}

    def verificar_horario_permitido(self, agora: time) -> bool:
        return _time_in_window(agora, self.config.kill_zone_inicio, self.config.kill_zone_fim)

    def janela_atual(self, agora: time) -> tuple[bool, str | None, str | None]:
        """
        Returns (permitido, janela_label, direcao_esperada)
        """
        if not self.verificar_horario_permitido(agora):
            return False, None, None

        for j in self.config.janelas_prioritarias:
            if _time_in_window(agora, j.inicio, j.fim):
                return True, f"{j.inicio.strftime('%H:%M')}-{j.fim.strftime('%H:%M')}", j.direcao_esperada

        return True, "OBSERVACAO", "AMBAS"

    def analisar_oportunidade(
        self,
        preco_atual: float,
        candle: dict[str, float],
        contexto: dict[str, Any],
        *,
        agora: time | None = None,
        day_key: date | None = None,
        direcao_esperada: str | None = None,
        step_dia: float | None = None,
    ) -> SinalOperacional | None:
        """
        Compatível com o uso:
            sinal = op.analisar_oportunidade(preco_atual, candle, contexto)
        """
        tz = ZoneInfo("Europe/Lisbon")
        now = datetime.now(tz)
        agora = agora or now.time()
        day_key = day_key or now.date()

        permitido, janela_label, janela_dir = self.janela_atual(agora)
        if not permitido:
            return None

        self._reset_if_new_day(day_key)

        if not janela_label:
            return None

        max_ops = int(self.config.max_operacoes_por_janela)
        used = int(self._ops_by_window.get(janela_label, 0))
        if used >= max_ops:
            return None

        # Override direction if caller provides (ex: backtest / forcing)
        direcao_esperada = (direcao_esperada or janela_dir or "AMBAS").upper()
        if direcao_esperada not in ("COMPRA", "VENDA", "AMBAS"):
            direcao_esperada = "AMBAS"

        niveis = self.analisador_niveis.get_niveis_psicologicos(float(preco_atual), step_dia=step_dia)
        if not niveis:
            return None

        step_eff = float(step_dia) if step_dia and step_dia > 0 else float(niveis[0].step)
        directions = ("COMPRA", "VENDA") if direcao_esperada == "AMBAS" else (direcao_esperada,)

        for nivel in niveis[:5]:
            for d in directions:
                rejeitou, forca = self.detector_rejeicao.detectar_rejeicao(candle, nivel.valor, d)
                if not rejeitou or forca < float(self.config.forca_rejeicao_min):
                    continue

                direcao = Direcao.COMPRA if d == "COMPRA" else Direcao.VENDA
                stop = CalculadorStopEstrutural.calcular_stop(
                    direcao, float(nivel.valor), contexto, stop_min=float(self.config.stop_minimo)
                )
                risco = CalculadorStopEstrutural.risco_pontos(float(preco_atual), float(stop))

                if risco < float(self.config.stop_apertado_limite):
                    continue

                if risco > float(self.config.stop_maximo):
                    stop = (
                        float(preco_atual) + float(self.config.stop_maximo)
                        if direcao == Direcao.VENDA
                        else float(preco_atual) - float(self.config.stop_maximo)
                    )
                    stop = round(float(stop), 2)
                    risco = CalculadorStopEstrutural.risco_pontos(float(preco_atual), float(stop))

                alvos = self.gerador_alvos.gerar_alvos(float(preco_atual), direcao, step_eff)
                if not alvos:
                    continue

                # Record usage for this window.
                self._ops_by_window[janela_label] = used + 1

                return SinalOperacional(
                    direcao=direcao,
                    entrada=round(float(preco_atual), 2),
                    stop=round(float(stop), 2),
                    alvos=alvos,
                    nivel_testado=float(nivel.valor),
                    forca_rejeicao=float(forca),
                    risco_pontos=float(risco),
                    janela=str(janela_label),
                    timestamp=datetime.now(),
                )

        return None

    def get_estatisticas(self) -> dict[str, Any]:
        return {
            "assertividade_esperada": float(self.config.assertividade_esperada),
            "total_operacoes_analisadas": 189,
            "rr_medio_compra": 0.91,
            "rr_medio_venda": 0.71,
            "stop_minimo_recomendado": float(self.config.stop_minimo),
            "stop_maximo_recomendado": float(self.config.stop_maximo),
            "horarios_validados": [
                "23:20-00:30 (VENDAS)",
                "00:30-01:30 (COMPRAS/VENDAS)",
                "03:00-04:00 (COMPRAS)",
                "05:00-06:00 (VENDAS)",
            ],
        }

