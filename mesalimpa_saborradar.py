"""
Bovinus MesaLimpa & SaborRadar - Modelo em Python
-------------------------------------------------
Dois motores de visão computacional:
  1. MesaLimpa  -> estado das mesas (LIVRE_LIMPA / OCUPADA / AGUARDANDO_LIMPEZA)
                   e alerta quando passa de 180 s aguardando limpeza.
  2. SaborRadar -> % de sobra no prato + item predominante, com alerta em tempo
                   real quando um item passa do limite numa janela de tempo.

Requisitos: pip install opencv-python numpy
Uso:        python mesalimpa_saborradar.py
"""

import json
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import cv2
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
CARDAPIO_SEMANA = {
    0: "Segunda (Virado à Paulista)",
    1: "Terça (Árabe)",
    2: "Quarta (Feijoada)",
    3: "Quinta (Italiano)",
    4: "Sexta (Frutos do Mar)",
}

PRACAS = {"Salão Principal": 35, "Salão Inferior": 25, "Salão Superior": 30}


@dataclass
class Config:
    limite_limpeza_seg: int = 180        # 3 min aguardando limpeza
    limite_sobra_prato: float = 20.0     # % do prato para considerar rejeição
    janela_sobra_min: int = 20           # janela de análise das sobras
    limite_item_alerta: float = 30.0     # % de pratos com rejeição p/ alertar
    min_amostras_item: int = 5           # evita alerta com poucos pratos


# ==============================================================================
# 1. SABORRADAR
# ==============================================================================
# Faixas HSV (H: 0-180 no OpenCV) para classificar o tipo de sobra
FAIXAS_ALIMENTO = {
    "Massa / Lasanha (molho vermelho)": ((0, 70, 50), (22, 255, 240)),
    "Arroz / Polenta / Queijo":         ((23, 45, 120), (34, 255, 255)),
    "Salada / Guarnição verde":         ((35, 50, 40), (85, 255, 255)),
    "Carne / Feijão (tons escuros)":    ((0, 0, 10), (180, 120, 90)),
}


@dataclass
class RegistroPrato:
    quando: datetime
    perc_sobra: float
    item: str
    rejeicao: bool


class SaborRadar:
    def __init__(self, config: Config, dia_semana: int = 3):
        self.cfg = config
        self.cardapio = CARDAPIO_SEMANA.get(dia_semana, "Fim de semana")
        self.historico: deque[RegistroPrato] = deque()

    def analisar_prato(self, imagem_bgr, quando: datetime | None = None) -> dict:
        quando = quando or datetime.now()
        h, w, _ = imagem_bgr.shape
        prato = imagem_bgr[int(h * .15):int(h * .85), int(w * .15):int(w * .85)]
        hsv = cv2.cvtColor(prato, cv2.COLOR_BGR2HSV)

        # Comida = tudo que NÃO é louça branca (saturação alta ou brilho baixo)
        mask_comida = cv2.inRange(hsv, np.array([0, 45, 30]), np.array([180, 255, 230]))
        area_total = prato.shape[0] * prato.shape[1]
        perc = round(float(np.count_nonzero(mask_comida)) / area_total * 100, 1)

        # Item predominante: faixa com mais pixels dentro da área de comida
        contagens = {}
        for nome, (lo, hi) in FAIXAS_ALIMENTO.items():
            m = cv2.inRange(hsv, np.array(lo), np.array(hi))
            contagens[nome] = int(np.count_nonzero(cv2.bitwise_and(m, mask_comida)))
        item = max(contagens, key=contagens.get)

        rejeicao = perc >= self.cfg.limite_sobra_prato
        reg = RegistroPrato(quando, perc, item if rejeicao else "Prato limpo", rejeicao)
        self.historico.append(reg)
        self._limpar_janela(quando)

        return {
            "timestamp": quando.strftime("%H:%M:%S"),
            "cardapio_dia": self.cardapio,
            "percentual_sobra_prato": perc,
            "rejeicao_significativa": rejeicao,
            "item_predominante_sobra": reg.item,
        }

    def _limpar_janela(self, agora: datetime):
        limite = agora - timedelta(minutes=self.cfg.janela_sobra_min)
        while self.historico and self.historico[0].quando < limite:
            self.historico.popleft()

    def ranking_itens(self) -> dict:
        """% de pratos com rejeição por item dentro da janela."""
        total = len(self.historico)
        if total == 0:
            return {}
        cont = defaultdict(int)
        for r in self.historico:
            if r.rejeicao:
                cont[r.item] += 1
        return {k: round(v / total * 100, 1)
                for k, v in sorted(cont.items(), key=lambda x: -x[1])}

    def alertas_qualidade(self) -> list[dict]:
        total = len(self.historico)
        if total < self.cfg.min_amostras_item:
            return []
        return [
            {
                "tipo": "QUALIDADE",
                "item": item,
                "percentual_pratos": perc,
                "mensagem": (f"{item} voltou em {perc}% dos pratos nos últimos "
                             f"{self.cfg.janela_sobra_min} min. Verificar cuba "
                             f"(temperatura/ressecamento/reposição)."),
            }
            for item, perc in self.ranking_itens().items()
            if perc >= self.cfg.limite_item_alerta
        ]

    def taxa_media_sobra(self) -> float:
        if not self.historico:
            return 0.0
        return round(sum(r.perc_sobra for r in self.historico) / len(self.historico), 1)


# ==============================================================================
# 2. MESALIMPA
# ==============================================================================
LIVRE_LIMPA, OCUPADA, AGUARDANDO = "LIVRE_LIMPA", "OCUPADA", "AGUARDANDO_LIMPEZA"


@dataclass
class Mesa:
    id: str
    praca: str
    estado: str = LIVRE_LIMPA
    desde: datetime | None = None   # quando entrou em AGUARDANDO_LIMPEZA


def classificar_estado(pessoas: int, objetos_na_mesa: int) -> str:
    """Saída do detector (YOLO etc.) por zona de mesa -> estado."""
    if pessoas > 0:
        return OCUPADA
    return AGUARDANDO if objetos_na_mesa > 0 else LIVRE_LIMPA


class MesaLimpa:
    def __init__(self, config: Config):
        self.cfg = config
        self.mesas: dict[str, Mesa] = {}
        n = 1
        for praca, qtd in PRACAS.items():
            for _ in range(qtd):
                mid = f"M-{n:02d}"
                self.mesas[mid] = Mesa(mid, praca)
                n += 1

    def atualizar(self, mesa_id: str, pessoas: int, objetos: int, agora: datetime):
        mesa = self.mesas[mesa_id]
        novo = classificar_estado(pessoas, objetos)
        if novo == AGUARDANDO and mesa.estado != AGUARDANDO:
            mesa.desde = agora
        if novo != AGUARDANDO:
            mesa.desde = None
        mesa.estado = novo

    def segundos_aguardando(self, mesa: Mesa, agora: datetime) -> int:
        return int((agora - mesa.desde).total_seconds()) if mesa.desde else 0

    def alertas_limpeza(self, agora: datetime) -> list[dict]:
        por_praca = defaultdict(list)
        for m in self.mesas.values():
            seg = self.segundos_aguardando(m, agora)
            if m.estado == AGUARDANDO and seg > self.cfg.limite_limpeza_seg:
                por_praca[m.praca].append({"mesa": m.id, "segundos": seg})
        return [
            {
                "tipo": "LIMPEZA",
                "praca": praca,
                "mesas_atrasadas": len(itens),
                "detalhes": sorted(itens, key=lambda x: -x["segundos"]),
                "mensagem": f"Maître de {praca}: acionar garçom — {len(itens)} mesa(s) sujas há mais de 3 min.",
            }
            for praca, itens in por_praca.items()
        ]

    def resumo(self, agora: datetime) -> dict:
        resumo = {}
        for praca, total in PRACAS.items():
            ms = [m for m in self.mesas.values() if m.praca == praca]
            sujas = [m for m in ms if m.estado == AGUARDANDO]
            resumo[praca] = {
                "total": total,
                "ocupadas": sum(m.estado == OCUPADA for m in ms),
                "aguardando_limpeza": len(sujas),
                "sujas_acima_3min": sum(
                    self.segundos_aguardando(m, agora) > self.cfg.limite_limpeza_seg for m in sujas),
                "livres": sum(m.estado == LIVRE_LIMPA for m in ms),
            }
        return resumo


# ==============================================================================
# SIMULAÇÃO (substitui CFTV e câmera de bancada para a demo)
# ==============================================================================
def gerar_prato(tipo: str | None, rng: random.Random):
    """Prato branco com uma porção de comida (BGR). tipo=None -> prato limpo."""
    img = np.ones((400, 400, 3), dtype=np.uint8) * 245
    if tipo is None:
        return img
    cores = {
        "Massa / Lasanha (molho vermelho)": (35, 75, 210),
        "Salada / Guarnição verde": (60, 170, 70),
        "Arroz / Polenta / Queijo": (60, 200, 235),
    }
    lado = rng.randint(130, 190)          # ~ 24% a 50% da área útil
    x = rng.randint(90, 400 - 90 - lado)
    y = rng.randint(90, 400 - 90 - lado)
    cv2.rectangle(img, (x, y), (x + lado, y + lado), cores[tipo], -1)
    return img


def simular_cenario(nome: str, hora: datetime, p_lasanha_sobra: float,
                    n_pratos: int, mesas_sujas_por_praca: dict, ocupacao: float,
                    cfg: Config, rng: random.Random) -> dict:
    radar = SaborRadar(cfg, dia_semana=3)
    mesalimpa = MesaLimpa(cfg)

    # --- Mesas: ocupadas / sujas (há mais de 3 min) / livres
    for praca in PRACAS:
        ids = [m.id for m in mesalimpa.mesas.values() if m.praca == praca]
        rng.shuffle(ids)
        n_ocup = int(len(ids) * ocupacao)
        n_sujas = mesas_sujas_por_praca.get(praca, 0)
        for i, mid in enumerate(ids):
            if i < n_ocup:
                mesalimpa.atualizar(mid, pessoas=3, objetos=6, agora=hora)
            elif i < n_ocup + n_sujas:
                saiu = hora - timedelta(seconds=rng.randint(200, 330))
                mesalimpa.atualizar(mid, pessoas=0, objetos=5, agora=saiu)
            else:
                mesalimpa.atualizar(mid, pessoas=0, objetos=0, agora=hora)

    # --- Pratos devolvidos nos últimos minutos
    for i in range(n_pratos):
        quando = hora - timedelta(seconds=int(cfg.janela_sobra_min * 60 * i / n_pratos))
        if rng.random() < 0.5:   # prato de lasanha
            tipo = "Massa / Lasanha (molho vermelho)" if rng.random() < p_lasanha_sobra else None
        else:
            tipo = rng.choice([None, None, None, "Salada / Guarnição verde",
                               "Arroz / Polenta / Queijo"])
        radar.analisar_prato(gerar_prato(tipo, rng), quando)

    return {
        "cenario": nome,
        "horario": hora.strftime("%H:%M"),
        "cardapio": radar.cardapio,
        "mesas_por_praca": mesalimpa.resumo(hora),
        "taxa_media_sobra_pct": radar.taxa_media_sobra(),
        "ranking_sobras_pct_pratos": radar.ranking_itens(),
        "alertas": mesalimpa.alertas_limpeza(hora) + radar.alertas_qualidade(),
    }


if __name__ == "__main__":
    cfg = Config()
    rng = random.Random(42)
    base = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

    cenarios = [
        # nome, hora, P(lasanha sobra), pratos, sujas/praça, ocupação
        ("Início do movimento", base, 0.08, 20,
         {"Salão Principal": 1, "Salão Inferior": 1, "Salão Superior": 0}, 0.40),
        ("Pico — gargalo no salão", base.replace(minute=50), 0.85, 30,
         {"Salão Principal": 7, "Salão Inferior": 2, "Salão Superior": 0}, 0.80),
        ("Após intervenção", base.replace(hour=13, minute=10), 0.10, 30,
         {"Salão Principal": 2, "Salão Inferior": 1, "Salão Superior": 0}, 0.65),
    ]

    for c in cenarios:
        resultado = simular_cenario(*c, cfg=cfg, rng=rng)
        print(f"\n===== {resultado['cenario'].upper()} ({resultado['horario']}) =====")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
