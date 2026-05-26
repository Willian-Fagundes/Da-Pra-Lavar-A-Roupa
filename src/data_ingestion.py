import os
import warnings
from datetime import datetime


import pandas as pd
import requests as r


from dotenv import load_dotenv
from methods import classificar, score_chuva, score_nuvens, score_temperatura, score_umidade, score_vento, agg_dia

warnings.filterwarnings("ignore")

load_dotenv(override=False)

API_KEY = os.getenv("API_KEY")

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

daily.to_csv("dados.csv", index = False)

