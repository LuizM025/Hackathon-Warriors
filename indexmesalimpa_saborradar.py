import json
from datetime import datetime

import cv2
import numpy as np


def detectar_sobra_prato(imagem_bgr, dia_semana="Quinta-feira (Italiano)"):
    h, w, _ = imagem_bgr.shape
    prato = imagem_bgr[int(h * 0.15) : int(h * 0.85), int(w * 0.15) : int(w * 0.85)]
    hsv = cv2.cvtColor(prato, cv2.COLOR_BGR2HSV)

    mask_comida = cv2.inRange(hsv, np.array([0, 45, 30]), np.array([180, 255, 230]))
    area_total = prato.shape[0] * prato.shape[1]
    perc_sobra = round((np.sum(mask_comida > 0) / area_total) * 100, 1)

    mask_molho_massa = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([22, 255, 240]))
    mask_folhas = cv2.inRange(hsv, np.array([35, 50, 40]), np.array([85, 255, 255]))

    if np.sum(mask_molho_massa > 0) > np.sum(mask_folhas > 0):
        item_provavel = "Massa / Lasanha ao Sugo ou Bolonhesa"
    else:
        item_provavel = "Salada / Guarnicao Verde"

    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "cardapio_dia": dia_semana,
        "percentual_sobra_prato": perc_sobra,
        "rejeicao_significativa": perc_sobra >= 20.0,
        "item_predominante_sobra": item_provavel if perc_sobra >= 20.0 else "Prato limpo (sem rejeicao)",
    }


def gerar_imagem_prato_com_sobra():
    img = np.ones((400, 400, 3), dtype=np.uint8) * 245
    cv2.rectangle(img, (130, 130), (275, 265), (35, 75, 210), -1)
    return img


def avaliar_mesas_praca(praca, mesas_monitoradas):
    alertas = []
    for m in mesas_monitoradas:
        if m["estado"] == "SUJA" and m["segundos_aguardando"] > 180:
            alertas.append(
                {
                    "mesa": m["id"],
                    "praca": praca,
                    "tempo_suja_seg": m["segundos_aguardando"],
                    "acao": f"Acionar garcom da praca {praca} imediatamente",
                }
            )
    return {
        "praca": praca,
        "total_alertas_limpeza": len(alertas),
        "detalhes": alertas,
    }


if __name__ == "__main__":
    img_teste = gerar_imagem_prato_com_sobra()
    res_sobra = detectar_sobra_prato(img_teste)
    print("=== RELATORIO SABORRADAR (RETORNO DE PRATOS) ===")
    print(json.dumps(res_sobra, indent=2, ensure_ascii=False))

    mesas_exemplo = [
        {"id": "M-12", "estado": "OCUPADA", "segundos_aguardando": 0},
        {"id": "M-14", "estado": "SUJA", "segundos_aguardando": 235},
        {"id": "M-19", "estado": "SUJA", "segundos_aguardando": 95},
        {"id": "M-21", "estado": "SUJA", "segundos_aguardando": 310},
    ]
    res_mesas = avaliar_mesas_praca("Salao Principal", mesas_exemplo)
    print("\n=== RELATORIO MESALIMPA (GIRO DE SALAO) ===")
    print(json.dumps(res_mesas, indent=2, ensure_ascii=False))
