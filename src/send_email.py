import os
import smtplib

import pandas as pd


from dotenv import load_dotenv

from methods import gerar_resumo_html
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

load_dotenv(override=False)

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")
SENHA_EMAIL = os.getenv("SENHA_EMAIL")
CITY = "Carapicuíba"

dados = pd.read_csv("dados.csv")

def enviar_email():
    msg = MIMEMultipart("related")
    msg["Subject"] = f"Resumo da semana - {CITY} — {datetime.today().strftime('%d/%m')}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = EMAIL_DESTINO

    # Corpo HTML
    msg.attach(MIMEText(gerar_resumo_html(CITY), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_REMETENTE, SENHA_EMAIL)
        smtp.send_message(msg)

    print(f"E-mail enviado para {EMAIL_DESTINO}")

enviar_email()