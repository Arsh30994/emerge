"""Configuration loader for the Singing Bowls Export Automation System."""

import os
from dotenv import load_dotenv

from utils import logger


load_dotenv()

REQUIRED_KEYS = {
    "SERPAPI_KEY": (
        "Get a free key at https://serpapi.com "
        "(250 searches/month on the free plan)."
    ),
    "HUNTER_API_KEY": (
        "Get a free key at https://hunter.io "
        "(50 Domain Search credits/month on the free plan)."
    ),
    "GMAIL_ADDRESS": (
        "Use the Gmail address that will send outreach emails."
    ),
    "GMAIL_APP_PASSWORD": (
        "Enable 2-Step Verification in Google Account → Security, "
        "then create an App Password (not your normal Gmail password)."
    ),
    "PRESENTATION_LINK": (
        "Paste a public Google Slides / Drive link to your company presentation."
    ),
}


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        missing = []
        for key, hint in REQUIRED_KEYS.items():
            value = os.getenv(key)
            if not value or not value.strip():
                missing.append(f"  - {key}: {hint}")

        if missing:
            message = (
                "Missing required environment variable(s).\n"
                "Copy .env.example to .env and fill in the values:\n"
                + "\n".join(missing)
            )
            logger.error(message)
            raise ValueError(message)

        self.serpapi_key = os.getenv("SERPAPI_KEY").strip()
        self.hunter_api_key = os.getenv("HUNTER_API_KEY").strip()
        self.gmail_address = os.getenv("GMAIL_ADDRESS").strip()
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD").strip()
        self.presentation_link = os.getenv("PRESENTATION_LINK").strip()
        self.company_name = os.getenv(
            "COMPANY_NAME", "Himalayan Singing Bowls Co."
        ).strip() or "Himalayan Singing Bowls Co."
        self.your_name = os.getenv(
            "YOUR_NAME", "Export Manager"
        ).strip() or "Export Manager"
        self.your_position = os.getenv(
            "YOUR_POSITION", "Sales Manager"
        ).strip() or "Sales Manager"
        self.contact_phone = os.getenv("CONTACT_PHONE", "").strip()


try:
    config = Config()
except ValueError:
    # Re-raise so importing modules still fails loudly when misconfigured,
    # but the detailed message is already in errors.log.
    raise
