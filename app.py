"""Flask dashboard for the Singing Bowls Export Automation System."""

import csv
import io
import traceback
from contextlib import redirect_stdout

from flask import Flask, jsonify, render_template

from email_enrichment import enrich_leads
from email_sender import send_outreach_emails
from lead_discovery import find_leads
from utils import log_exception, logger, user_friendly_error


app = Flask(__name__)

activity_log = []
MAX_LOG_ENTRIES = 50


def add_log(message):
    """Append a message to the in-memory activity log."""
    activity_log.append(message)
    if len(activity_log) > MAX_LOG_ENTRIES:
        del activity_log[: len(activity_log) - MAX_LOG_ENTRIES]


def count_csv_rows(path):
    """Return the number of data rows in a CSV file, or 0 if missing/unreadable."""
    try:
        with open(path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)
            return sum(1 for _ in reader)
    except (FileNotFoundError, OSError, csv.Error):
        return 0


def count_emails_sent(path="email_log.csv"):
    """Count successfully sent emails from the outreach log."""
    try:
        with open(path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            return sum(1 for row in reader if row.get("status") == "sent")
    except (FileNotFoundError, OSError, csv.Error):
        return 0


def count_emails_enriched(path="leads.csv"):
    """Count leads that have at least one email address."""
    try:
        with open(path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            return sum(1 for row in reader if (row.get("emails") or "").strip())
    except (FileNotFoundError, OSError, csv.Error):
        return 0


def load_enriched_leads(path="leads.csv"):
    """Load enriched leads for the leads table page."""
    try:
        with open(path, newline="", encoding="utf-8") as csvfile:
            return list(csv.DictReader(csvfile))
    except (FileNotFoundError, OSError, csv.Error):
        return []


def get_dashboard_stats():
    """Collect dashboard counters for templates and JSON APIs."""
    return {
        "leads_found": count_csv_rows("leads_raw.csv"),
        "emails_enriched": count_emails_enriched("leads.csv"),
        "emails_sent": count_emails_sent("email_log.csv"),
        "raw_leads": count_csv_rows("leads_raw.csv"),
        "enriched_leads": count_csv_rows("leads.csv"),
    }


def capture_output(func, *args, **kwargs):
    """Run a function while capturing printed stdout for the activity log."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    output = buffer.getvalue().strip()
    if output:
        for line in output.splitlines():
            add_log(line)
    return result


@app.route("/")
def index():
    """Dashboard home page."""
    stats = get_dashboard_stats()
    return render_template(
        "index.html",
        stats=stats,
        activity_log=list(reversed(activity_log[-20:])),
    )


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Return current dashboard stats as JSON for dynamic updates."""
    return jsonify(get_dashboard_stats())


@app.route("/leads")
def leads_page():
    """Display enriched leads in a table."""
    leads = load_enriched_leads("leads.csv")
    return render_template("leads.html", leads=leads)


@app.route("/api/find-leads", methods=["POST"])
def api_find_leads():
    """Trigger SerpAPI lead discovery."""
    try:
        add_log("Starting lead discovery...")
        logger.info("API: find-leads started")
        leads = capture_output(find_leads)
        count = len(leads) if leads else 0
        add_log(f"Lead discovery complete: {count} leads found.")
        return jsonify(
            {
                "status": "success",
                "message": f"Found {count} leads.",
                "leads_found": count,
                "stats": get_dashboard_stats(),
            }
        )
    except Exception as exc:
        log_exception("API find-leads failed", exc)
        add_log(f"Lead discovery failed: {exc}")
        traceback.print_exc()
        return jsonify(
            {
                "status": "error",
                "message": user_friendly_error(exc),
            }
        ), 500


@app.route("/api/enrich-emails", methods=["POST"])
def api_enrich_emails():
    """Trigger Hunter.io email enrichment."""
    try:
        add_log("Starting email enrichment...")
        logger.info("API: enrich-emails started")
        enriched = capture_output(enrich_leads)
        total = len(enriched) if enriched else 0
        with_emails = sum(1 for row in (enriched or []) if row.get("emails"))
        add_log(
            f"Email enrichment complete: {total} leads, {with_emails} with emails."
        )
        return jsonify(
            {
                "status": "success",
                "message": f"Enriched {total} leads ({with_emails} with emails).",
                "leads_processed": total,
                "leads_with_emails": with_emails,
                "stats": get_dashboard_stats(),
            }
        )
    except Exception as exc:
        log_exception("API enrich-emails failed", exc)
        add_log(f"Email enrichment failed: {exc}")
        traceback.print_exc()
        return jsonify(
            {
                "status": "error",
                "message": user_friendly_error(exc),
            }
        ), 500


@app.route("/api/send-emails", methods=["POST"])
def api_send_emails():
    """Trigger Gmail SMTP outreach."""
    try:
        add_log("Starting email outreach...")
        logger.info("API: send-emails started")
        summary = capture_output(send_outreach_emails) or {}
        if summary.get("error"):
            add_log(f"Outreach warning: {summary['error']}")
            return jsonify(
                {
                    "status": "error",
                    "message": user_friendly_error(summary["error"]),
                    "attempted": summary.get("attempted", 0),
                    "sent": summary.get("sent", 0),
                    "failed": summary.get("failed", 0),
                    "stats": get_dashboard_stats(),
                }
            ), 400

        attempted = summary.get("attempted", 0)
        sent = summary.get("sent", 0)
        failed = summary.get("failed", 0)
        add_log(
            f"Outreach complete: {sent} sent, {failed} failed "
            f"({attempted} attempted)."
        )
        return jsonify(
            {
                "status": "success",
                "message": f"Sent {sent} of {attempted} emails ({failed} failed).",
                "attempted": attempted,
                "sent": sent,
                "failed": failed,
                "stats": get_dashboard_stats(),
            }
        )
    except Exception as exc:
        log_exception("API send-emails failed", exc)
        add_log(f"Email outreach failed: {exc}")
        traceback.print_exc()
        return jsonify(
            {
                "status": "error",
                "message": user_friendly_error(exc),
            }
        ), 500


if __name__ == "__main__":
    logger.info("Starting Flask app on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
