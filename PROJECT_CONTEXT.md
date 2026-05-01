# AI Buddy Event Collector — Project Context & Progress

> This document captures the full context of the project so far.
> Hand this to Claude Code (or any AI assistant) to continue development seamlessly.

---

## What is this project?

This is **Repo 1** of the AI Buddy project — a New Media Lab course project at Radboud University, supervised by Dr. Evelien Heyselaar.

**AI Buddy** is a mobile app (React Native / Expo) that acts as a supportive AI companion for international students (age 18-30) in Nijmegen, Netherlands, to combat loneliness. The key differentiator is that AI Buddy doesn't just provide emotional support — it **encourages real-world social engagement** by suggesting nearby events, activities, and social opportunities.

The project has 3 repos:
- **ai-buddy-event-collector** (THIS REPO) — Scrapes, extracts, and stores events from Nijmegen organizations
- **ai-buddy-chatbot** — FastAPI backend + AI agent that serves the mobile app, reads events from the shared database
- **ai-buddy-app** — Expo React Native mobile app (frontend)

## Architecture Overview

```
[This Repo: Event Collector]
  Scrapers (Instagram, websites, recurring YAML)
      ↓
  Raw content (captions, HTML, images)
      ↓
  LLM extraction (Gemini free tier)
      ↓
  Deduplicate + validate
      ↓
  Shared Database (Supabase PostgreSQL)
      ↑
  Reads from
      ↑
[Chatbot Repo: AI Buddy API]
  Expo App ↔ FastAPI ↔ AI Agent → queries events DB
```

## Tech Stack (all free)

| Component | Tool |
|-----------|------|
| Language | Python 3.11+ |
| Database | Supabase (free tier, PostgreSQL) |
| Instagram scraping | Instaloader |
| Website scraping (JS) | Crawl4AI (wraps Playwright) |
| Website scraping (static) | BeautifulSoup + httpx |
| LLM extraction | Gemini API (free tier) — but built to be swappable |
| Data validation | Pydantic |
| Recurring events | YAML config files |
| Geocoding | Nominatim (OpenStreetMap, free) |

## Project Structure

```
ai-buddy-event-collector/
├── config/
│   ├── __init__.py
│   ├── settings.py                  # ✅ DONE — loads env vars
│   ├── Nijmegen_Student_Organizations_Database.csv  # ✅ DONE — 63 orgs with websites & Instagram
│   └── recurring_events.yaml        # ❌ TODO — manual recurring events (Meet & Eat, pub quizzes)
├── scrapers/
│   ├── __init__.py
│   ├── base.py                      # ✅ DONE — abstract BaseScraper interface
│   ├── instagram_scraper.py         # ❌ TODO — Instaloader-based
│   ├── website_scraper.py           # ❌ TODO — Crawl4AI-based
│   ├── static_scraper.py            # ❌ TODO — BeautifulSoup for simple sites
│   └── recurring_loader.py          # ❌ TODO — loads from YAML config
├── extraction/
│   ├── __init__.py
│   ├── schemas.py                   # ✅ DONE — Event and RawContent Pydantic models
│   ├── base_llm.py                  # ✅ DONE — abstract BaseLLMExtractor interface
│   └── llm_extractor.py             # ❌ TODO — Gemini implementation of BaseLLMExtractor
├── pipeline/
│   ├── runner.py                    # ❌ TODO — orchestrates full pipeline
│   ├── deduplicator.py              # ❌ TODO — fuzzy match on title + date + location
│   └── geocoder.py                  # ❌ TODO — address → lat/lng (skippable for prototype)
├── db/
│   ├── __init__.py
│   └── supabase_client.py           # ✅ DONE — insert, upsert, query, existence check
├── main.py                          # ❌ TODO — entry point
├── .env                             # ✅ DONE — has SUPABASE_URL and SUPABASE_KEY
├── requirements.txt                 # ✅ DONE
├── test_connection.py               # ✅ DONE — verified Supabase connection works
└── README.md                        # ✅ DONE
```

## What has been completed

### 1. Supabase database
- Project created and running
- `events` table created with this schema:

| Column | Type | Constraints |
|--------|------|-------------|
| id | uuid | PK, default: gen_random_uuid() |
| title | text | NOT NULL |
| description | text | nullable |
| organizer | text | NOT NULL |
| date | date | NOT NULL |
| start_time | time | nullable |
| end_time | time | nullable |
| location_name | text | nullable |
| address | text | nullable |
| category | text | nullable |
| cost | text | nullable |
| language | text | nullable |
| source_url | text | nullable |
| source_platform | text | nullable |
| image_url | text | nullable |
| created_at | timestamptz | default: now() |

- Note: we intentionally skipped `latitude`, `longitude`, and `expires_at` — not needed for prototype
- Connection tested and working (insert + read + delete verified)

### 2. Core files written

**config/settings.py** — Loads all env vars: SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, LLM_PROVIDER, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

**extraction/schemas.py** — Two Pydantic models:
- `Event` — matches the Supabase table schema exactly
- `RawContent` — what scrapers output (organizer, text, image_url, source_url, source_platform, scraped_at)

**scrapers/base.py** — Abstract `BaseScraper` with one method: `scrape(org: dict) -> list[RawContent]`

**extraction/base_llm.py** — Abstract `BaseLLMExtractor` with one method: `extract_events(raw_content: RawContent) -> list[Event]`

**db/supabase_client.py** — `SupabaseClient` class with methods: `insert_event()`, `insert_events()`, `get_events_by_organizer()`, `event_exists()`

### 3. Organizations database
- CSV file with ~63 Nijmegen organizations
- Includes: student associations, study associations, bars/pubs, cultural venues, community orgs
- Has columns for: name, type, website, Instagram handle, event types, frequency, language, relevance to international students

## What needs to be built next (in this order)

### Step 1: Gemini LLM Extractor
File: `extraction/llm_extractor.py`

- Implement `BaseLLMExtractor` using Google's Gemini API (free tier)
- Use `google-genai` package (already in requirements.txt)
- Send raw content (caption text + optionally image) to Gemini
- Prompt it to return structured JSON matching the Event schema
- Parse response into Event objects
- Add GEMINI_API_KEY to .env

Key design principle: the extractor should be swappable. To add OpenAI or Ollama later, just create a new class implementing BaseLLMExtractor. The pipeline picks which one to use based on `LLM_PROVIDER` in settings.

### Step 2: Instagram Scraper
File: `scrapers/instagram_scraper.py`

- Implement `BaseScraper` using Instaloader
- Read Instagram handles from the organizations CSV
- Fetch recent posts (last 7-14 days) for each account
- Extract caption text and image URLs
- Return as list of RawContent objects
- Add rate limiting / delays between accounts to avoid Instagram blocks
- Needs INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env

### Step 3: Recurring Events Loader
File: `scrapers/recurring_loader.py` + `config/recurring_events.yaml`

- Define known recurring events in YAML (Meet & Eat Wednesdays, pub quizzes, etc.)
- Loader reads YAML and generates concrete Event objects for the next 4 weeks
- No scraping or LLM needed — these are hardcoded schedules
- Implement BaseScraper interface

### Step 4: Pipeline Runner
File: `pipeline/runner.py` + `main.py`

- Orchestrate: load orgs → scrape → extract → deduplicate → store
- For each org in CSV, check its source type and run appropriate scraper
- Feed raw content through LLM extractor
- Check if event already exists in DB (deduplication via `event_exists()`)
- Insert new events into Supabase
- Log progress and errors

### Step 5: Website Scraper (later)
File: `scrapers/website_scraper.py`

- Implement BaseScraper using Crawl4AI
- For venues with proper event pages (Doornroosje, LUX, De Lindenberg)
- Crawl4AI returns markdown from JS-rendered pages
- Feed to LLM extractor same as Instagram content

### Step 6 (optional): Deduplicator
File: `pipeline/deduplicator.py`

- Fuzzy matching on title + date + organizer to catch near-duplicates across sources
- For prototype, the exact match in `event_exists()` is sufficient

## Key Design Principles

1. **Modular LLM**: Don't hardcode Gemini. Use the `BaseLLMExtractor` interface so any model can be swapped in via config
2. **Modular scrapers**: Each source type implements `BaseScraper`. Adding a new org = adding a line to CSV + config, not writing code
3. **Modular DB**: `SupabaseClient` could be swapped for SQLite for local testing
4. **Config-driven**: Organizations, recurring events, and scraper settings all live in config files, not code
5. **Free everything**: This is a student project with no budget. Every tool choice must have a free tier

## Environment Variables Needed

```
# Already set up
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...

# Still needed
GEMINI_API_KEY=           # Get from https://ai.google.dev/
LLM_PROVIDER=gemini       # Options: gemini, openai, ollama
INSTAGRAM_USERNAME=        # For Instaloader
INSTAGRAM_PASSWORD=        # For Instaloader
```

## Event Categories (standardized)

Use these values for the `category` field:
social, pub_quiz, board_games, sports, cultural, food, music, workshop, party, language_exchange, networking, religious, other

## Important Context

- Target users are international students age 18-30 at Radboud University in Nijmegen
- Events should be in English or bilingual — Dutch-only events are lower priority
- Key recurring events to capture: Meet & Eat (Wednesdays, Studentenkerk), pub quizzes at various bars, ESN events
- Instagram is the primary source — most student associations post events there as designed flyers (images with text), so the LLM extractor needs to handle both caption text AND image analysis
- The chatbot repo reads from the same Supabase `events` table, so the schema must stay consistent

## Team

| Name | Student Number |
|------|---------------|
| Aditya Ghadge | s1157350 |
| David Magaram | s1168483 |
| Abhinav Reddy Ramireddy | s1113089 |
| Aneesh Varma Rudraraju | s1170909 |

Stakeholder: Dr. E.S. Heyselaar — Radboud University