"""Email enrichment via Hunter.io Domain Search API."""

import csv
import time
from urllib.parse import urlparse

import requests

from config import config
from utils import log_exception, logger


HUNTER_DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"
MAX_EMAILS_PER_DOMAIN = 3
REQUEST_DELAY_SECONDS = 1


def extract_domain(website):
    """Extract a bare domain from a website URL (e.g. example.com)."""
    if not website:
        return ""

    url = website.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    host = (parsed.netloc or parsed.path).lower()
    host = host.split("/")[0]
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def fetch_emails_for_domain(domain, api_key):
    """
    Call Hunter.io Domain Search for a domain.

    Returns a list of up to MAX_EMAILS_PER_DOMAIN email addresses.
    On failure, returns an empty list and logs the error.
    """
    params = {"domain": domain, "api_key": api_key}

    try:
        response = requests.get(
            HUNTER_DOMAIN_SEARCH_URL,
            params=params,
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        log_exception(f"Hunter.io network error for {domain}", exc)
        print(f"  Network error for {domain}: {exc}")
        return []

    if response.status_code == 401:
        logger.error("Hunter.io invalid API key for domain %s", domain)
        print(f"  Invalid Hunter.io API key (401) for {domain}")
        return []

    if response.status_code == 429:
        logger.warning("Hunter.io rate limit for %s — waiting 60s", domain)
        print(f"  Rate limited by Hunter.io for {domain}. Waiting 60s...")
        time.sleep(60)
        try:
            response = requests.get(
                HUNTER_DOMAIN_SEARCH_URL,
                params=params,
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            log_exception(f"Hunter.io network error on retry for {domain}", exc)
            print(f"  Network error on retry for {domain}: {exc}")
            return []

    if response.status_code != 200:
        try:
            error_body = response.json()
            message = error_body.get("errors", error_body)
        except ValueError:
            message = response.text
        logger.error(
            "Hunter.io API error for %s (%s): %s",
            domain,
            response.status_code,
            message,
        )
        print(f"  Hunter.io API error for {domain} ({response.status_code}): {message}")
        return []

    try:
        data = response.json().get("data", {})
    except ValueError as exc:
        log_exception(f"Invalid JSON from Hunter.io for {domain}", exc)
        print(f"  Invalid JSON response for {domain}")
        return []

    emails = []
    for entry in data.get("emails", []):
        value = entry.get("value")
        if value and value not in emails:
            emails.append(value)
        if len(emails) >= MAX_EMAILS_PER_DOMAIN:
            break

    if not emails:
        logger.info("No emails found for domain %s", domain)

    return emails


def enrich_leads(
    input_file="leads_raw.csv",
    output_file="leads.csv",
    max_enrichments=50,
):
    """
    Enrich leads from input_file with emails from Hunter.io Domain Search.

    Skips domains that fail and continues with the rest.
    """
    try:
        with open(input_file, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            leads = list(reader)
    except FileNotFoundError:
        logger.error("Input file not found: %s", input_file)
        print(f"Input file not found: {input_file}")
        return []
    except OSError as exc:
        log_exception(f"Could not read {input_file}", exc)
        print(f"Could not read {input_file}: {exc}")
        return []

    if not leads:
        print(f"No leads found in {input_file}")
        return []

    processed_domains = set()
    domain_email_cache = {}
    domains_enriched = 0
    total_emails_found = 0
    leads_with_no_emails = 0
    failed_domains = 0
    enriched_leads = []

    enrichment_cap = max_enrichments
    logger.info(
        "Starting enrichment: %s leads, cap=%s domains",
        len(leads),
        enrichment_cap,
    )
    print(f"Loaded {len(leads)} leads from {input_file}")
    print(f"Will enrich up to {enrichment_cap} unique domains")

    for lead in leads:
        website = lead.get("website", "")
        domain = extract_domain(website)
        emails = []

        if not domain:
            print(f"  Skipping lead with no valid domain: {website}")
        elif domain in processed_domains:
            emails = domain_email_cache.get(domain, [])
            print(f"  Reusing cached emails for {domain}")
        elif domains_enriched >= enrichment_cap:
            print(f"  Enrichment cap reached ({enrichment_cap}). Skipping {domain}")
        else:
            domains_enriched += 1
            print(f"Enriching domain {domains_enriched}/{enrichment_cap}: {domain}")
            try:
                emails = fetch_emails_for_domain(domain, config.hunter_api_key)
            except Exception as exc:
                failed_domains += 1
                log_exception(f"Unexpected enrichment failure for {domain}", exc)
                print(f"  Skipping failed domain {domain}: {exc}")
                emails = []

            processed_domains.add(domain)
            domain_email_cache[domain] = emails
            total_emails_found += len(emails)

            if emails:
                print(f"Found {len(emails)} emails for {domain}")
            else:
                failed_domains += 1
                print(f"Found 0 emails for {domain}")

            time.sleep(REQUEST_DELAY_SECONDS)

        emails_str = ";".join(emails)
        if not emails:
            leads_with_no_emails += 1

        enriched_leads.append(
            {
                "company": lead.get("company", ""),
                "website": website,
                "snippet": lead.get("snippet", ""),
                "source_query": lead.get("source_query", ""),
                "emails": emails_str,
            }
        )

    fieldnames = ["company", "website", "snippet", "source_query", "emails"]
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(enriched_leads)
    except OSError as exc:
        log_exception(f"Could not write {output_file}", exc)
        print(f"Could not write {output_file}: {exc}")
        return enriched_leads

    print("\n--- Enrichment Summary ---")
    print(f"Total leads processed: {len(enriched_leads)}")
    print(f"Total domains enriched: {domains_enriched}")
    print(f"Total emails found: {total_emails_found}")
    print(f"Leads with no emails: {leads_with_no_emails}")
    print(f"Domains with no/failed results: {failed_domains}")
    print(f"Saved enriched leads to {output_file}")

    logger.info(
        "Enrichment finished: processed=%s enriched=%s emails=%s no_email=%s",
        len(enriched_leads),
        domains_enriched,
        total_emails_found,
        leads_with_no_emails,
    )
    return enriched_leads


if __name__ == "__main__":
    enrich_leads()
