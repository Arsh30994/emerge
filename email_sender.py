"""Email outreach via Gmail SMTP."""

import csv
import smtplib
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText

from config import config
from utils import log_exception, logger


SUBJECT = (
    "Authentic Himalayan Singing Bowls – Wholesale Partnership Opportunity"
)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_DELAY_SECONDS = 2.5


def _send_delay():
    """Shorter pause in DEMO_MODE so the dashboard stays responsive."""
    return 0.15 if getattr(config, "demo_mode", False) else EMAIL_DELAY_SECONDS


def build_email_body(lead_company):
    """Build a personalized outreach email body."""
    return f"""Hi,

I'm reaching out from {config.company_name}. We manufacture authentic Himalayan singing bowls, meditation chimes, and gongs.

We're looking to partner with wholesalers, importers, and wellness retailers like {lead_company}. You can view our company presentation here:
{config.presentation_link}

If this is relevant for you, I'd be happy to share our catalog, pricing, and samples.

Best regards,
{config.your_name}
{config.your_position}
{config.company_name}
{config.contact_phone}
"""


def send_single_email(to_address, lead_company):
    """
    Send one outreach email via Gmail SMTP.

    Returns (success: bool, error_message: str).
    """
    if "@" not in to_address or "." not in to_address.split("@")[-1]:
        return False, f"Invalid email address: {to_address}"

    if getattr(config, "demo_mode", False):
        # Simulate a successful send without hitting Gmail.
        _ = build_email_body(lead_company or "your company")
        print(f"  DEMO_MODE: simulated send to {to_address}")
        return True, ""

    body = build_email_body(lead_company or "your company")
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = SUBJECT
    message["From"] = config.gmail_address
    message["To"] = to_address

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.gmail_address, config.gmail_app_password)
            server.sendmail(config.gmail_address, [to_address], message.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError as exc:
        log_exception(f"SMTP auth failed for {to_address}", exc)
        return False, (
            "SMTP authentication failed. Check GMAIL_ADDRESS and "
            f"GMAIL_APP_PASSWORD in .env. Details: {exc}"
        )
    except smtplib.SMTPRecipientsRefused as exc:
        log_exception(f"SMTP recipient refused: {to_address}", exc)
        return False, f"Recipient refused: {exc}"
    except smtplib.SMTPSenderRefused as exc:
        log_exception(f"SMTP sender refused for {to_address}", exc)
        return False, f"Sender refused: {exc}"
    except smtplib.SMTPConnectError as exc:
        log_exception(f"SMTP connection error for {to_address}", exc)
        return False, f"Could not connect to Gmail SMTP: {exc}"
    except smtplib.SMTPException as exc:
        log_exception(f"SMTP error for {to_address}", exc)
        return False, f"SMTP error: {exc}"
    except OSError as exc:
        log_exception(f"Network error sending to {to_address}", exc)
        return False, f"Network error: {exc}"
    except Exception as exc:
        log_exception(f"Unexpected send error for {to_address}", exc)
        return False, f"Unexpected error: {exc}"


def _append_log(log_file, rows):
    """Append log rows to email_log.csv, creating the file with a header if needed."""
    fieldnames = ["timestamp", "company", "email", "status", "error_message"]
    try:
        with open(log_file, "x", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except FileExistsError:
        with open(log_file, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerows(rows)


def send_outreach_emails(input_file="leads.csv", log_file="email_log.csv"):
    """
    Send personalized outreach emails to enriched leads.

    Continues with the next address if individual sends fail.
    """
    try:
        with open(input_file, newline="", encoding="utf-8") as csvfile:
            leads = list(csv.DictReader(csvfile))
    except FileNotFoundError:
        logger.error("Input file not found: %s", input_file)
        print(f"Input file not found: {input_file}")
        return {
            "attempted": 0,
            "sent": 0,
            "failed": 0,
            "error": f"File not found: {input_file}",
        }
    except OSError as exc:
        log_exception(f"Could not read {input_file}", exc)
        print(f"Could not read {input_file}: {exc}")
        return {"attempted": 0, "sent": 0, "failed": 0, "error": str(exc)}

    queue = []
    for lead in leads:
        emails_field = (lead.get("emails") or "").strip()
        if not emails_field:
            continue
        company = lead.get("company", "")
        for email in emails_field.split(";"):
            address = email.strip()
            if address:
                queue.append((company, address))

    total = len(queue)
    if total == 0:
        print("No emails found to send.")
        return {"attempted": 0, "sent": 0, "failed": 0}

    logger.info("Starting outreach: %s email(s) queued", total)
    print(f"Preparing to send {total} email(s)")

    attempted = 0
    sent = 0
    failed = 0
    log_rows = []

    for index, (company, address) in enumerate(queue, start=1):
        attempted += 1
        print(f"Sending to email {index}/{total}: {address}")

        success, error_message = send_single_email(address, company)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        if success:
            sent += 1
            status = "sent"
            print(f"Sent successfully to {address}")
        else:
            failed += 1
            status = "failed"
            logger.error("Failed to send to %s: %s", address, error_message)
            print(f"Failed to send to {address}: {error_message}")

        log_rows.append(
            {
                "timestamp": timestamp,
                "company": company,
                "email": address,
                "status": status,
                "error_message": error_message,
            }
        )

        if index < total:
            time.sleep(_send_delay())

    try:
        _append_log(log_file, log_rows)
        print(f"Logged {len(log_rows)} attempt(s) to {log_file}")
    except OSError as exc:
        log_exception(f"Could not write log file {log_file}", exc)
        print(f"Could not write log file {log_file}: {exc}")

    print("\n--- Outreach Summary ---")
    print(f"Total emails attempted: {attempted}")
    print(f"Total sent successfully: {sent}")
    print(f"Total failed: {failed}")

    logger.info(
        "Outreach finished: attempted=%s sent=%s failed=%s",
        attempted,
        sent,
        failed,
    )
    return {"attempted": attempted, "sent": sent, "failed": failed}


if __name__ == "__main__":
    send_outreach_emails()
