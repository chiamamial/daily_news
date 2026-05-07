import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(subject: str, html: str) -> None:
    sender = os.environ["GMAIL_USER"].strip()
    password = "".join(c for c in os.environ["GMAIL_APP_PASSWORD"] if ord(c) < 128).strip()
    recipient = os.environ.get("RECIPIENT_EMAIL", sender).strip()

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"Email inviata a {recipient}")
