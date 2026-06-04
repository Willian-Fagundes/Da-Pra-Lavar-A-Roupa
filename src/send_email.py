import os
import smtplib
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

load_dotenv(override=True)

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
SENHA_EMAIL = os.getenv("SENHA_EMAIL")

def enviar_email(city, email_destino):
    from utils import gerar_resumo_html

    msg = MIMEMultipart("related")
    msg["Subject"] = f"Resumo da semana - {city} — {datetime.today().strftime('%d/%m')}"
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = email_destino

    # Corpo HTML
    msg.attach(MIMEText(gerar_resumo_html(city), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_REMETENTE, SENHA_EMAIL)
        smtp.send_message(msg)

    print(f"E-mail enviado para {email_destino}")