import smtplib
from email.mime.text import MIMEText
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM


class EmailTool:
    name = "send_email"
    description = (
        "Envia email via SMTP. Requer configuração em config.py (SMTP_HOST, SMTP_USER, etc.). "
        "Input: {'to': 'dest@email.com', 'subject': 'Assunto', 'body': 'Mensagem'}"
    )

    def run(self, input_data: dict) -> str:
        if not SMTP_HOST or not SMTP_USER:
            return (
                "Email não configurado. Preencha em config.py: "
                "SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM."
            )

        to      = input_data.get("to", "").strip()
        subject = input_data.get("subject", "").strip()
        body    = input_data.get("body", "").strip()

        if not to:
            return "Erro: campo 'to' obrigatório."
        if not subject:
            return "Erro: campo 'subject' obrigatório."

        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"]    = EMAIL_FROM or SMTP_USER
            msg["To"]      = to
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            return f"Email enviado para {to} — assunto: {subject}"
        except Exception as e:
            return f"Erro ao enviar email: {str(e)}"
