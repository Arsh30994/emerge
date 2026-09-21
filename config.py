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

PLACEHOLDER_MARKERS = (
    "your_serpapi_key_here",
    "your_hunter_key_here",
    "your.email@gmail.com",
    "your_gmail_app_password",
    "your-presentation-link",
    "demo_",
)


def _is_placeholder(value):
    if not value or not value.strip():
        return True
    lower = value.strip().lower()
    return any(marker in lower for marker in PLACEHOLDER_MARKERS)


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        demo_flag = os.getenv("DEMO_MODE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        values = {key: (os.getenv(key) or "").strip() for key in REQUIRED_KEYS}
        missing = [
            f"  - {key}: {hint}"
            for key, hint in REQUIRED_KEYS.items()
            if not values[key]
        ]

        # Per-service: use the real API when that credential looks real.
        self.use_real_serpapi = not _is_placeholder(values.get("SERPAPI_KEY", ""))
        self.use_real_hunter = not _is_placeholder(values.get("HUNTER_API_KEY", ""))
        self.use_real_gmail = (
            not _is_placeholder(values.get("GMAIL_ADDRESS", ""))
            and not _is_placeholder(values.get("GMAIL_APP_PASSWORD", ""))
        )

        all_placeholders = not (
            self.use_real_serpapi or self.use_real_hunter or self.use_real_gmail
        )
        self.demo_mode = demo_flag or all_placeholders

        if missing and not self.demo_mode and all_placeholders:
            message = (
                "Missing required environment variable(s).\n"
                "Copy .env.example to .env and fill in the values:\n"
                + "\n".join(missing)
                + "\n\nOr set DEMO_MODE=true to run with sample data."
            )
            logger.error(message)
            raise ValueError(message)

        if missing:
            for key in REQUIRED_KEYS:
                if not values[key]:
                    values[key] = f"demo_{key.lower()}"

        if self.demo_mode:
            logger.info(
                "DEMO_MODE on - SerpAPI real=%s, Hunter real=%s, Gmail real=%s",
                self.use_real_serpapi,
                self.use_real_hunter,
                self.use_real_gmail,
            )

        self.serpapi_key = values["SERPAPI_KEY"]
        self.hunter_api_key = values["HUNTER_API_KEY"]
        self.gmail_address = values["GMAIL_ADDRESS"]
        self.gmail_app_password = values["GMAIL_APP_PASSWORD"]
        self.presentation_link = values["PRESENTATION_LINK"]
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


config = Config()
