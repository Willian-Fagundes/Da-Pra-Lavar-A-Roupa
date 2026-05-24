import os
import warnings

import pandas as pd
import requests as r
import numpy as np
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from methods import classificar, score_chuva, score_nuvens, score_temperatura, score_umidade, score_vento

warnings.filterwarnings("ignore")

load_dotenv(override= True)

API_KEY = os.getenv("OPEN_WEATHER_API")
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

fig, axes = plt.subplots(3, 1, figsize=(12, 12))
fig.suptitle(f"🧺 Viabilidade para Lavar Roupa — {CITY}",
             fontsize=15, fontweight="bold", y=0.98)

datas  = [d.strftime("%a\n%d/%m") for d in daily["date"]]
scores = daily["score_final"].tolist()
cores  = daily["cor"].tolist()

# Gráfico 1: Nota final
ax1 = axes[0]
bars = ax1.bar(datas, scores, color=cores, edgecolor="white", linewidth=1.5, width=0.6)
ax1.set_ylim(0, 10.5)
ax1.set_ylabel("Nota (0–10)")
ax1.set_title("Nota de Viabilidade (critério 2 dias de secagem)")
ax1.axhline(y=6, color="gray", linestyle="--", alpha=0.5, label="Mínimo recomendado")
ax1.legend()
for bar, score, clf in zip(bars, scores, daily["classificacao"]):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
             f"{score}", ha="center", va="bottom", fontweight="bold", fontsize=11)
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
             clf.split(" ")[0], ha="center", va="center", fontsize=14)
ax1.set_facecolor("#f8f9fa")
ax1.grid(axis="y", alpha=0.3)

# Gráfico 2: Fatores individuais
ax2 = axes[1]
x = np.arange(len(datas))
w = 0.16
fatores = {
    "Sem Chuva":   (daily["s_chuva"]  * 10, "#3498db"),
    "Umidade":     (daily["s_umid"]   * 10, "#9b59b6"),
    "Temperatura": (daily["s_temp"]   * 10, "#e74c3c"),
    "Vento":       (daily["s_vento"]  * 10, "#1abc9c"),
    "Nuvens":      (daily["s_nuvens"] * 10, "#f39c12"),
}
for i, (label, (vals, cor)) in enumerate(fatores.items()):
    ax2.bar(x + (i - 2) * w, vals, w * 0.9, label=label, color=cor, alpha=0.85)
ax2.set_xticks(x)
ax2.set_xticklabels(datas)
ax2.set_ylim(0, 11)
ax2.set_ylabel("Sub-nota (0–10)")
ax2.set_title("Decomposição por Fator")
ax2.legend(ncol=5, fontsize=9)
ax2.set_facecolor("#f8f9fa")
ax2.grid(axis="y", alpha=0.3)

# Gráfico 3: Chuva
ax3  = axes[2]
ax3b = ax3.twinx()
ax3.bar(datas, daily["prob_chuva_max"] * 100, color="#3498db",
        alpha=0.6, width=0.5, label="Prob. chuva (%)")
ax3b.plot(datas, daily["chuva_total_mm"], color="#1a5276",
          marker="o", linewidth=2, label="Chuva acum. (mm)")
ax3.set_ylabel("Probabilidade (%)", color="#3498db")
ax3b.set_ylabel("Chuva Acumulada (mm)", color="#1a5276")
ax3.set_ylim(0, 110)
ax3.set_title("Risco de Chuva por Dia")
ax3.set_facecolor("#f8f9fa")
ax3.grid(axis="y", alpha=0.3)
lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3b.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, fontsize=9)

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig("dapralavar.png", bbox_inches="tight", dpi=150)
plt.show()