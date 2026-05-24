import os
import warnings
import smtplib


import pandas as pd
import requests as r
import numpy as np
import matplotlib.pyplot as plt

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

from dotenv import load_dotenv
from methods import classificar, score_chuva, score_nuvens, score_temperatura, score_umidade, score_vento

warnings.filterwarnings("ignore")

load_dotenv(override= True)

API_KEY = os.getenv("OPEN_WEATHER_API")
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")
SENHA_EMAIL = os.getenv("SENHA_EMAIL")

CITY = "Carapicuíba"
UNITS = "metric"

DIAS_SECAGEM = 2

URL = "https://api.openweathermap.org/data/2.5/forecast"

response = r.get(URL, params={"q": CITY, "appid": API_KEY,
                                  "units": UNITS, "lang": "pt_br"})
response.raise_for_status()

raw = response.json()

df = pd.json_normalize(raw["list"], sep = "_")
weather_df = pd.json_normalize([row["weather"][0] for row in raw["list"]]).add_prefix("weather_")

df = df.drop(columns=["weather"]).reset_index(drop=True)
df = pd.concat([df, weather_df], axis=1)

df["dt_txt"] = pd.to_datetime(df["dt_txt"])
df["date"] = df["dt_txt"].dt.date
df["hour"] = df["dt_txt"].dt.hour

if "rain_3h" not in df.columns:
    df["rain_3h"] = 0.0
df["rain_3h"] = df["rain_3h"].fillna(0.0)

df= df.rename(columns={"main_temp" : "temp",
                       "main_humidity" : "humidity",
                       "wind_speed" : "wind_speed",
                       "clouds_all" : "clouds_pct",
                       "pop" : "prob_chuva"})

cols = ["dt_txt","date","hour","temp","humidity","wind_speed",
        "clouds_pct","prob_chuva","rain_3h","weather_description"]

df = df[cols]

print(f"Período: {df['date'].min()} → {df['date'].max()}")
print(f"Registros: {len(df)} slots de 3h")
df.head(8)

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

daily = df.groupby("date").apply(agg_dia).reset_index()
daily["date"] = pd.to_datetime(daily["date"])

VARIAVEIS = {
    "prob_chuva":  "negativa",   
    "humidity":    "negativa",  
    "temp":        "positiva",   
    "wind_speed":  "positiva",  
    "clouds_pct":  "negativa",  
}

corr_target = "prob_chuva"
corr_vars   = ["humidity", "temp", "wind_speed", "clouds_pct"]

corr_series = df[corr_vars + [corr_target]].corr()[corr_target].drop(corr_target)

print("Correlação com probabilidade de chuva:")
print(corr_series.round(3))

pesos_brutos = corr_series.abs()

pesos_brutos["prob_chuva"] = pesos_brutos.mean() * 2

PESOS_CORR = (pesos_brutos / pesos_brutos.sum()).to_dict()

PESOS = {
    "chuva":       PESOS_CORR["prob_chuva"],
    "umidade":     PESOS_CORR["humidity"],
    "temperatura": PESOS_CORR["temp"],
    "vento":       PESOS_CORR["wind_speed"],
    "nuvens":      PESOS_CORR["clouds_pct"],
}

print("\nPesos calculados por correlação:")
for k, v in sorted(PESOS.items(), key=lambda x: -x[1]):
    print(f"  {k:<14} {v:.3f}  ({v*100:.1f}%)")

daily["s_chuva"]  = daily.apply(lambda r: score_chuva(r.prob_chuva_max, r.chuva_total_mm), axis=1)
daily["s_umid"]   = daily["umidade_media"].apply(score_umidade)
daily["s_temp"]   = daily["temp_media"].apply(score_temperatura)
daily["s_vento"]  = daily["vento_medio"].apply(score_vento)
daily["s_nuvens"] = daily["nuvens_media"].apply(score_nuvens)

daily["score_base"] = (
    PESOS["chuva"]       * daily["s_chuva"]  +
    PESOS["umidade"]     * daily["s_umid"]   +
    PESOS["temperatura"] * daily["s_temp"]   +
    PESOS["vento"]       * daily["s_vento"]  +
    PESOS["nuvens"]      * daily["s_nuvens"]
) * 10

# Penalizador de janela (2 dias seguintes)
penalidades = []
for i in range(len(daily)):
    janela = daily.iloc[i+1 : i+1+DIAS_SECAGEM]
    if len(janela) == 0:
        penalidades.append(1.0)
        continue
    pior_prob = janela["prob_chuva_max"].max()
    pior_mm   = janela["chuva_total_mm"].max()
    penalidades.append(score_chuva(pior_prob, pior_mm))

daily["fator_janela"] = penalidades
daily["score_final"]  = (0.60 * daily["score_base"] +
                         0.40 * daily["score_base"] * daily["fator_janela"])
daily["score_final"]  = daily["score_final"].clip(0, 10).round(1)


daily[["classificacao","cor"]] = daily["score_final"].apply(
    lambda s: pd.Series(classificar(s)))

cols_show = ["date","score_final","classificacao","prob_chuva_max",
             "chuva_total_mm","umidade_media","temp_media","vento_medio",
             "nuvens_media","descricao"]

print(daily[cols_show])


def gerar_resumo_html():
    cores_html = {
        "✅ Ótimo":    "#2ecc71",
        "👍 Bom":      "#27ae60",
        "😐 Regular":  "#f39c12",
        "⚠️ Ruim":     "#e67e22",
        "❌ Péssimo":  "#e74c3c",
    }

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
        <h2>Da pra lavar a roupa ? — {CITY}</h2>
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


def enviar_email():
    msg = MIMEMultipart("related")
    msg["Subject"] = f"REsumo da semana - {CITY} — {datetime.today().strftime('%d/%m')}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = EMAIL_DESTINO

    # Corpo HTML
    msg.attach(MIMEText(gerar_resumo_html(), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_REMETENTE, SENHA_EMAIL)
        smtp.send_message(msg)

    print(f"E-mail enviado para {EMAIL_DESTINO}")

enviar_email()