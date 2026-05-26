import numpy as np
import pandas as pd
from datetime import datetime



def agg_dia(g):
    diurno = g[g["hour"].between(6, 20)]  # período útil de secagem

    return pd.Series({
        "prob_chuva_max":  g["prob_chuva"].max(),
        "chuva_total_mm":  g["rain_3h"].sum(),
        "umidade_media":   diurno["humidity"].mean()   if len(diurno) else g["humidity"].mean(),
        "temp_media":      diurno["temp"].mean()       if len(diurno) else g["temp"].mean(),
        "vento_medio":     diurno["wind_speed"].mean() if len(diurno) else g["wind_speed"].mean(),
        "nuvens_media":    diurno["clouds_pct"].mean() if len(diurno) else g["clouds_pct"].mean(),
        "n_slots_chuva":   (g["rain_3h"] > 0).sum(),
        "descricao":       g["weather_description"].mode().iloc[0],
    })


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


def gerar_resumo_html(city):
    cores_html = {
        "✅ Ótimo":    "#2ecc71",
        "👍 Bom":      "#27ae60",
        "😐 Regular":  "#f39c12",
        "⚠️ Ruim":     "#e67e22",
        "❌ Péssimo":  "#e74c3c",
    }
    daily = pd.read_csv("dados.csv", parse_dates=["date"])
    linhas_tabela = ""
    for _, row in daily.sort_values("date").iterrows():
        data  = row["date"].strftime("%a %d/%m")
        cor   = row["cor"]
        clf   = row["classificacao"]
        nota  = row["score_final"]
        chuva = row["prob_chuva_max"]
        desc  = row["descricao"]
        pen   = "⚠️ janela ruim" if row["fator_janela"] < 0.5 else ""

        linhas_tabela += f"""
        <tr>
            <td>{data}</td>
            <td style="color:{cor}; font-weight:bold">{clf}</td>
            <td style="font-weight:bold">{nota:.1f}</td>
            <td>{chuva:.0%}</td>
            <td>{desc} {pen}</td>
        </tr>"""

    melhor = daily.loc[daily["score_final"].idxmax()]
    alerta = ""
    if daily["score_final"].max() < 6:
        alerta = "<p>⚠️ <b>Nenhum dia ótimo esta semana</b> — considere aguardar nova previsão.</p>"

    return f"""
    <html><body style="font-family:Arial,sans-serif; max-width:600px; margin:auto">
        <h2>Da pra lavar a roupa ? — {city}</h2>
        <p style="color:gray">{datetime.today().strftime('%d/%m/%Y às %H:%M')}</p>

        <table border="1" cellpadding="8" cellspacing="0"
               style="border-collapse:collapse; width:100%">
            <thead style="background:#f0f0f0">
                <tr>
                    <th>Data</th>
                    <th>Classificação</th>
                    <th>Nota</th>
                    <th>Chuva</th>
                    <th>Condição</th>
                </tr>
            </thead>
            <tbody>{linhas_tabela}</tbody>
        </table>

        <p>🏆 <b>Melhor dia:</b> {melhor["date"].strftime("%A, %d/%m")}
           (nota {melhor["score_final"]:.1f} — {melhor["classificacao"]})</p>

        {alerta}

        <p style="color:gray; font-size:12px">Gráfico detalhado em anexo.</p>
    </body></html>
    """


