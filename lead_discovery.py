"""Lead discovery via SerpAPI for singing bowl buyers."""

import csv
import time
from urllib.parse import urlparse

from config import config
from utils import log_exception, logger

try:
    from serpapi import GoogleSearch
except ImportError:  # pragma: no cover - fallback package name
    try:
        from serpapi.google_search import GoogleSearch
    except ImportError:
        GoogleSearch = None


SEARCH_QUERIES = [
    "singing bowls wholesale buyer email",
    "singing bowls importer USA contact",
    "singing bowls meditation shop contact us",
    "singing bowls yoga store wholesale",
    "buy singing bowls bulk importer",
]

BUSINESS_KEYWORDS = (
    "wholesale",
    "import",
    "shop",
    "store",
    "buyer",
    "company",
    "trading",
)

DEMO_LEADS = [
    {
        "company": "Lotus Wellness Wholesale",
        "website": "https://www.lotuswellnesswholesale.com",
        "snippet": "Wholesale importer of meditation and singing bowls for yoga stores across the USA.",
        "source_query": "singing bowls wholesale buyer email",
    },
    {
        "company": "Zen Imports Trading Co.",
        "website": "https://www.zenimportstrading.com",
        "snippet": "Bulk buyer and importer of Himalayan singing bowls and gongs for retailers.",
        "source_query": "singing bowls importer USA contact",
    },
    {
        "company": "Mindful Living Shop",
        "website": "https://www.mindfullivingshop.com",
        "snippet": "Meditation shop specializing in singing bowls, chimes, and wellness gifts.",
        "source_query": "singing bowls meditation shop contact us",
    },
    {
        "company": "Om Yoga Store",
        "website": "https://www.omyogastore.com",
        "snippet": "Yoga store wholesale partner seeking authentic singing bowls and meditation tools.",
        "source_query": "singing bowls yoga store wholesale",
    },
    {
        "company": "Sacred Sound Importers",
        "website": "https://www.sacredsoundimporters.com",
        "snippet": "Company importing singing bowls in bulk for wellness retailers and spas.",
        "source_query": "buy singing bowls bulk importer",
    },
    {
        "company": "Himalaya Trade Partners",
        "website": "https://www.himalayatradepartners.com",
        "snippet": "Trading company sourcing wholesale singing bowls from Nepal and India.",
        "source_query": "singing bowls wholesale buyer email",
    },
    {
        "company": "Calm Collective Retail",
        "website": "https://www.calmcollectiveretail.com",
        "snippet": "Boutique shop and wholesale buyer for meditation bowls and sound healing kits.",
        "source_query": "singing bowls meditation shop contact us",
    },
    {
        "company": "Pacific Wellness Imports",
        "website": "https://www.pacificwellnessimports.com",
        "snippet": "Importer of singing bowls and yoga accessories for West Coast stores.",
        "source_query": "singing bowls importer USA contact",
    },
]

REQUEST_DELAY_SECONDS = 3
OUTPUT_CSV = "leads_raw.csv"


def _normalize_website(url):
    """Normalize a URL for duplicate detection."""
    if not url:
        return ""
    parsed = urlparse(url.strip().lower())
    netloc = parsed.netloc.removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{netloc}{path}"


def _company_from_title(title):
    """Derive a company name from a search result title."""
    if not title:
        return "Unknown"
    for separator in (" | ", " - ", " – ", " — "):
        if separator in title:
            title = title.split(separator)[0]
            break
    return title.strip() or "Unknown"


def _looks_like_business(title, snippet, link):
    """Keep results that mention business-related keywords."""
    text = f"{title} {snippet} {link}".lower()
    return any(keyword in text for keyword in BUSINESS_KEYWORDS)


def _demo_find_leads(num_leads):
    """Return sample leads when DEMO_MODE is enabled."""
    print("DEMO_MODE: generating sample singing-bowl buyer leads...")
    leads = DEMO_LEADS[: max(1, min(num_leads, len(DEMO_LEADS)))]
    for index, query in enumerate(SEARCH_QUERIES, start=1):
        print(f"Searching query {index}/{len(SEARCH_QUERIES)}: {query}")
        matched = sum(1 for lead in leads if lead["source_query"] == query)
        print(f"Found {matched} leads for this query ({len(leads)} total so far)")
        time.sleep(0.2)
    _save_leads_csv(leads)
    print(f"Saved {len(leads)} leads to {OUTPUT_CSV}")
    logger.info("DEMO_MODE lead discovery finished: %s leads", len(leads))
    return leads


def _search_google(query):
    """Run a single Google search via SerpAPI. Returns organic results or []."""
    if GoogleSearch is None:
        logger.error("SerpAPI client not installed. Run: pip install google-search-results")
        print("  SerpAPI client missing. Install google-search-results.")
        return []

    params = {
        "engine": "google",
        "q": query,
        "api_key": config.serpapi_key,
        "num": 10,
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as exc:
        log_exception(f"SerpAPI network/request error for '{query}'", exc)
        print(f"  Network/API error for '{query}': {exc}")
        return []

    if "error" in results:
        error_msg = results["error"]
        lower = str(error_msg).lower()
        if "invalid" in lower and "key" in lower:
            logger.error("SerpAPI invalid API key: %s", error_msg)
            print(f"  Invalid SerpAPI key: {error_msg}")
        elif "rate" in lower or "limit" in lower or "quota" in lower:
            logger.error("SerpAPI rate limit: %s", error_msg)
            print(f"  SerpAPI rate limit hit: {error_msg}")
        else:
            logger.error("SerpAPI error for '%s': %s", query, error_msg)
            print(f"  SerpAPI error for '{query}': {error_msg}")
        return []

    return results.get("organic_results", [])


def find_leads(num_leads=20):
    """
    Discover potential singing bowl buyers using SerpAPI Google search.

    Returns a list of dicts with keys: company, website, snippet, source_query.
    Also writes leads_raw.csv. Continues even if individual queries fail.
    """
    if getattr(config, "demo_mode", False) and not getattr(
        config, "use_real_serpapi", False
    ):
        return _demo_find_leads(num_leads)

    leads = []
    seen_websites = set()
    total_queries = len(SEARCH_QUERIES)
    failed_queries = 0

    logger.info("Starting lead discovery (target=%s)", num_leads)
    print(f"Starting lead discovery (target={num_leads})...")

    for index, query in enumerate(SEARCH_QUERIES, start=1):
        if len(leads) >= num_leads:
            break

        print(f"Searching query {index}/{total_queries}: {query}")

        try:
            organic_results = _search_google(query)
            if not organic_results:
                failed_queries += 1
        except Exception as exc:
            failed_queries += 1
            log_exception(f"Unexpected failure on query '{query}'", exc)
            print(f"  Skipping failed query: {exc}")
            organic_results = []

        for result in organic_results:
            if len(leads) >= num_leads:
                break

            title = result.get("title", "")
            link = result.get("link", "")
            snippet = result.get("snippet", "")

            if not link:
                continue
            if not _looks_like_business(title, snippet, link):
                continue

            normalized = _normalize_website(link)
            if not normalized or normalized in seen_websites:
                continue

            seen_websites.add(normalized)
            leads.append(
                {
                    "company": _company_from_title(title),
                    "website": link,
                    "snippet": snippet,
                    "source_query": query,
                }
            )

        print(f"Found {len(leads)} leads so far")

        if index < total_queries and len(leads) < num_leads:
            time.sleep(REQUEST_DELAY_SECONDS)

    try:
        _save_leads_csv(leads)
        print(f"Saved {len(leads)} leads to {OUTPUT_CSV}")
    except OSError as exc:
        log_exception(f"Failed to write {OUTPUT_CSV}", exc)
        print(f"Could not save {OUTPUT_CSV}: {exc}")

    logger.info(
        "Lead discovery finished: %s leads, %s query failures",
        len(leads),
        failed_queries,
    )
    return leads


def _save_leads_csv(leads):
    """Write leads to leads_raw.csv."""
    fieldnames = ["company", "website", "snippet", "source_query"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)


if __name__ == "__main__":
    find_leads()
