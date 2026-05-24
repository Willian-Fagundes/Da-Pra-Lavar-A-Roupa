import numpy as np

def score_chuva(prob, mm):
    s_prob = 1 - prob
    s_mm   = np.clip(1 - mm / 10, 0, 1)
    return 0.6 * s_prob + 0.4 * s_mm

def score_umidade(hum):
    return np.clip((90 - hum) / 30, 0, 1)

def score_temperatura(temp):
    if temp >= 22:
        return np.clip(1 - (temp - 35) / 15, 0, 1)
    return np.clip((temp - 10) / 12, 0, 1)

def score_vento(spd):
    spd_kmh = spd * 3.6
    if spd_kmh <= 35:
        return np.clip(spd_kmh / 35, 0.1, 1)
    return np.clip(1 - (spd_kmh - 35) / 40, 0.1, 1)

def score_nuvens(cld):
    return 1 - cld / 100

def classificar(s):
    if s >= 8.0: return ("Ótimo",   "#2ecc71")
    if s >= 6.0: return ("Bom",     "#27ae60")
    if s >= 4.5: return ("Regular", "#f39c12")
    if s >= 3.0: return ("Ruim",    "#e67e22")
    return             ("Péssimo",  "#e74c3c")

