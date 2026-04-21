import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_pdf(pdf_path: str) -> None:
    sender = os.environ["GMAIL_USER"].strip()
    # Strip whitespace and non-ASCII chars that can appear when copy-pasting from Google
    password = "".join(c for c in os.environ["GMAIL_APP_PASSWORD"] if ord(c) < 128).strip()
    recipient = os.environ.get("RECIPIENT_EMAIL", sender).strip()

    date_str = datetime.now().strftime("%d %B %Y")
    filename = f"vibe_coding_{datetime.now().strftime('%Y%m%d')}.pdf"

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = f"Vibe Coding Daily — {date_str}"

    body = (
        f"Ciao,\n\n"
        f"Ecco la tua presentazione Vibe Coding del {date_str}.\n\n"
        f"Buona lettura!"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"Email inviata a {recipient}")
