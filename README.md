# Singing Bowls Export Automation System

A Flask web app that helps singing bowl exporters find wholesale buyers, enrich contact emails, and send personalized outreach — using free-tier APIs.

## Features

- **Lead discovery** – Search Google via SerpAPI for wholesalers, importers, and wellness retailers
- **Email enrichment** – Look up contact emails with Hunter.io Domain Search
- **Outreach emails** – Send personalized partnership emails through Gmail SMTP
- **Web dashboard** – One-click actions, live stats, activity log, and leads table
- **CSV exports** – `leads_raw.csv`, `leads.csv`, and `email_log.csv` for demos and review
- **Robust error handling** – Failures are logged to `errors.log` without stopping the whole pipeline

## Tech stack

| Layer | Tools |
|-------|--------|
| Web app | Python, Flask, Jinja2 |
| Search | SerpAPI (Google results) |
| Enrichment | Hunter.io Domain Search API |
| Email | Gmail SMTP (TLS, port 587) |
| Config | `python-dotenv`, `.env` |

## Setup

### 1. Clone / open the project

```bash
cd singing-bowl-export
```

If you are using the GitHub repo:

```bash
git clone https://github.com/Arsh30994/emerge.git
cd emerge
# or cd into singing-bowl-export if that is the project folder
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your real values.

### 5. Get API keys and credentials

#### SerpAPI (lead discovery)

1. Sign up at [https://serpapi.com](https://serpapi.com)
2. Copy your API key from the dashboard
3. Paste it as `SERPAPI_KEY` in `.env`
4. Free plan: **250 searches/month**

#### Hunter.io (email enrichment)

1. Sign up at [https://hunter.io](https://hunter.io)
2. Open API settings and copy your key
3. Paste it as `HUNTER_API_KEY` in `.env`
4. Free plan: **50 credits/month** (1 Domain Search = 1 credit)

#### Gmail App Password (sending email)

1. Use a Gmail account and turn on **2-Step Verification**
2. Go to Google Account → Security → **App passwords**
3. Create an app password for “Mail”
4. Set:
   - `GMAIL_ADDRESS` = your Gmail address
   - `GMAIL_APP_PASSWORD` = the 16-character app password (not your normal password)

Also set:

- `PRESENTATION_LINK` – public link to your company deck
- Optional: `COMPANY_NAME`, `YOUR_NAME`, `YOUR_POSITION`, `CONTACT_PHONE`

## How to run

```bash
python app.py
```

Then open: [http://localhost:5000](http://localhost:5000)

### Demo mode

By default `.env.example` sets `DEMO_MODE=true`. With placeholder keys, the app simulates Find Leads / Enrich Emails / Send Emails so you can demo the dashboard without burning API credits. Set `DEMO_MODE=false` and real keys when you want live SerpAPI, Hunter.io, and Gmail.

## How to use the dashboard

1. **Find Leads**  
   Calls SerpAPI with singing-bowl buyer queries, filters for business-like results, deduplicates websites, and writes `leads_raw.csv`.

2. **Enrich Emails**  
   Reads `leads_raw.csv`, extracts each domain, calls Hunter.io Domain Search (up to 50 domains), and writes `leads.csv` with an `emails` column.

3. **Send Emails**  
   Reads `leads.csv`, sends personalized outreach via Gmail SMTP for each email, and appends results to `email_log.csv`.

4. **View Leads** (`/leads`)  
   Shows a table of company, website, and emails from `leads.csv`.

Tip: Run the buttons **in order**. Each step depends on the CSV from the previous one.

## File structure

```text
singing-bowl-export/
├── app.py                 # Flask dashboard & API routes
├── config.py              # Loads and validates .env settings
├── lead_discovery.py      # SerpAPI lead finder
├── email_enrichment.py    # Hunter.io email enrichment
├── email_sender.py        # Gmail SMTP outreach
├── utils.py               # Shared logging & error helpers
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── static/
│   └── style.css
└── templates/
    ├── index.html         # Dashboard
    └── leads.html         # Leads table
```

Generated at runtime (gitignored):

- `leads_raw.csv` – discovered leads
- `leads.csv` – enriched leads
- `email_log.csv` – send attempts
- `errors.log` – error log

## Free tier limits (and how to stretch them)

| Service | Free limit | Tips |
|---------|------------|------|
| SerpAPI | 250 searches/month | App uses ~5 queries per run; keep `num_leads` modest |
| Hunter.io | 50 credits/month | Default `max_enrichments=50`; duplicate domains are cached and not recharged |
| Gmail | Daily send limits apply | Built-in 2.5s delay between emails; start with a small list for demos |

Maximize demos by:

1. Finding ~15–20 leads once
2. Enriching only domains that look like real shops/importers
3. Sending a short batch (5–10 emails) for the live demo

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| App won’t start / missing env vars | Copy `.env.example` → `.env` and fill every required key. Check `errors.log`. |
| SerpAPI errors | Confirm `SERPAPI_KEY`. Wait if you hit rate/quota limits. |
| Hunter returns no emails | Normal for some domains. Check key/credits. Review `errors.log`. |
| Gmail “authentication failed” | Use an **App Password**, not your normal password. Ensure 2FA is on. |
| Empty dashboard stats | Run **Find Leads** first, then enrich, then send. |
| Buttons hang a long time | Expected — API calls are sequential. Watch the activity log. |

## Assignment demo checklist

- [ ] `.env` filled with working SerpAPI, Hunter, and Gmail credentials
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `python app.py` starts without errors
- [ ] Dashboard loads at http://localhost:5000
- [ ] **Find Leads** creates `leads_raw.csv` and updates “Leads found”
- [ ] **Enrich Emails** creates `leads.csv` with some emails
- [ ] **/leads** page shows the table
- [ ] **Send Emails** updates `email_log.csv` and “Emails sent”
- [ ] Presentation link in the email body opens correctly
- [ ] Can briefly explain free-tier limits and the 3-step flow

## License

Created for academic / assignment use.
