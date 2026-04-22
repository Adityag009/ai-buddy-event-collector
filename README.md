# AI Buddy Event Collector

Automated event collection pipeline for the [AI Buddy](https://github.com/ai-buddy-chatbot) project. Scrapes, extracts, and stores events from student organizations, venues, and communities in Nijmegen — so the AI Buddy chatbot can suggest real-world social activities to international students.

> **Part of the AI Buddy project** — New Media Lab, Radboud University
> Stakeholder: Dr. E.S. Heyselaar

## How it works

```
Organizations DB (CSV)
        │
        ▼
┌─────────────────────────────┐
│   Scrapers (per source)     │
│  ┌───────────┐ ┌──────────┐ │
│  │ Instagram │ │ Websites │ │
│  │(Instaloader)│(Crawl4AI)│ │
│  └───────────┘ └──────────┘ │
│  ┌───────────┐ ┌──────────┐ │
│  │  Static   │ │ Recurring│ │
│  │(Beautiful │ │  (YAML)  │ │
│  │   Soup)   │ │          │ │
│  └───────────┘ └──────────┘ │
└─────────────┬───────────────┘
              ▼
     Raw content (captions,
      HTML, images)
              │
              ▼
┌─────────────────────────────┐
│  LLM Extraction (Gemini)   │
│  → title, date, time,      │
│    location, category       │
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│  Deduplicate + Geocode      │
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│  Supabase (PostgreSQL)      │
│  Shared with chatbot repo   │
└─────────────────────────────┘
```

## Project structure

```
ai-buddy-event-collector/
├── config/
│   ├── organizations.csv          # Master list of 60+ Nijmegen orgs
│   ├── recurring_events.yaml      # Manual recurring events (pub quizzes, Meet & Eat, etc.)
│   └── scraper_config.yaml        # Per-org scraper settings (method, selectors, frequency)
├── scrapers/
│   ├── base.py                    # Base scraper interface
│   ├── instagram_scraper.py       # Instaloader — Instagram posts + captions
│   ├── website_scraper.py         # Crawl4AI — JS-rendered event pages
│   ├── static_scraper.py          # BeautifulSoup — simple HTML sites
│   └── recurring_loader.py        # Loads recurring events from YAML config
├── extraction/
│   ├── llm_extractor.py           # Gemini API — raw content → structured event
│   └── schemas.py                 # Pydantic models (Event, Organization)
├── pipeline/
│   ├── runner.py                  # Orchestrates full pipeline
│   ├── deduplicator.py            # Fuzzy matching on title + date + location
│   └── geocoder.py                # Address → lat/lng (Nominatim, free)
├── db/
│   └── supabase_client.py         # Read/write to shared Supabase instance
├── main.py                        # Entry point
├── .env.example                   # Required environment variables
├── requirements.txt
└── README.md
```

## Tech stack

| Component | Tool | Cost |
|-----------|------|------|
| Instagram scraping | [Instaloader](https://instaloader.github.io/) | Free |
| Website scraping (JS) | [Crawl4AI](https://github.com/unclecode/crawl4ai) | Free |
| Website scraping (static) | BeautifulSoup + httpx | Free |
| LLM extraction | [Gemini API](https://ai.google.dev/) (free tier) | Free |
| Geocoding | [Nominatim](https://nominatim.org/) (OpenStreetMap) | Free |
| Database | [Supabase](https://supabase.com/) (free tier) | Free |
| Scheduling | cron / GitHub Actions | Free |

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_ORG/ai-buddy-event-collector.git
cd ai-buddy-event-collector
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
```

### 5. Run the pipeline

```bash
# Full pipeline (all sources)
python main.py

# Specific source only
python main.py --source instagram
python main.py --source websites
python main.py --source recurring
```

## Scraper methods

**Instagram** — Uses Instaloader to fetch recent posts from organization accounts listed in `organizations.csv`. Captions and images are sent to Gemini for event extraction. Run with delays to avoid rate limiting.

**Websites** — Uses Crawl4AI for JavaScript-heavy sites (Doornroosje, LUX, etc.) that render event calendars dynamically. Falls back to BeautifulSoup for simpler static pages.

**Recurring events** — No scraping needed. Events like "Meet & Eat every Wednesday at Studentenkerk" are defined in `recurring_events.yaml` and auto-generated for upcoming dates.

## Adding a new organization

1. Add a row to `config/organizations.csv`
2. Add scraper settings to `config/scraper_config.yaml`:

```yaml
esn_nijmegen:
  method: instagram          # instagram | crawl4ai | beautifulsoup | recurring
  instagram: esnnijmegen
  website: https://esnnijmegen.nl/events
  frequency: daily            # how often to scrape
  priority: high
```

3. Run `python main.py` — the pipeline picks it up automatically.

## Event schema

Each extracted event is stored with the following fields:

```python
class Event:
    id: str                   # Auto-generated UUID
    title: str                # Event name
    description: str          # Short description
    organizer: str            # Organization name
    date: date                # Event date
    start_time: time          # Start time
    end_time: time | None     # End time (if available)
    location_name: str        # Venue name
    address: str | None       # Street address
    latitude: float | None    # Geocoded
    longitude: float | None   # Geocoded
    category: str             # social | pub_quiz | sports | cultural | food | music | workshop | party | language | other
    cost: str | None          # free | paid | donation
    language: str             # english | dutch | both
    source_url: str | None    # Original post/page URL
    source_platform: str      # instagram | website | manual
    image_url: str | None     # Event flyer/image
    created_at: datetime      # When we scraped it
    expires_at: datetime      # Auto-cleanup after event date
```

## Database

Uses Supabase (PostgreSQL) shared with the [ai-buddy-chatbot](https://github.com/YOUR_ORG/ai-buddy-chatbot) repo. The chatbot reads from the `events` table to suggest activities to students.

### Tables

- `events` — All scraped and extracted events
- `organizations` — Master list of organizations (synced from CSV)
- `scrape_logs` — Track last scrape time, errors, and stats per org

## Scheduling

For the prototype, run manually. For production, set up a cron job or GitHub Actions workflow:

```yaml
# .github/workflows/scrape.yml
name: Scrape Events
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:       # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

## Related repos

- [ai-buddy-chatbot](https://github.com/YOUR_ORG/ai-buddy-chatbot) — FastAPI backend + AI agent that serves the mobile app
- [ai-buddy-app]((https://github.com/AneeshVarmaR/AI-BUDDY-APP)) — Expo React Native mobile app

## Team

| Name | Student Number |
|------|---------------|
| Aditya Ghadge | s1157350 |
| David Magaram | s1168483 |
| Abhinav Reddy Ramireddy | s1113089 |
| Aneesh Varma Rudraraju | s1170909 |

**Stakeholder:** Dr. E.S. Heyselaar — Radboud University

## License

Built for educational purposes as part of the New Media Lab course at Radboud University.
