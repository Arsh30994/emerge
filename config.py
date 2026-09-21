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
)


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
        missing = [f"  - {key}: {hint}" for key, hint in REQUIRED_KEYS.items() if not values[key]]
        looks_like_placeholder = any(
            not values[key]
            or any(marker in values[key].lower() for marker in PLACEHOLDER_MARKERS)
            for key in REQUIRED_KEYS
        )

        self.demo_mode = demo_flag or looks_like_placeholder

        if missing and not self.demo_mode:
            message = (
                "Missing required environment variable(s).\n"
                "Copy .env.example to .env and fill in the values:\n"
                + "\n".join(missing)
                + "\n\nOr set DEMO_MODE=true to run with sample data."
            )
            logger.error(message)
            raise ValueError(message)

        if missing and self.demo_mode:
            logger.warning(
                "Running in DEMO_MODE with incomplete .env — API calls will be simulated."
            )
            for key in REQUIRED_KEYS:
                if not values[key]:
                    values[key] = f"demo_{key.lower()}"

        if self.demo_mode:
            logger.info(
                "DEMO_MODE enabled - using simulated leads/emails when APIs are unavailable."
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
