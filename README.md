# Space Daily — starter website

A separate, static-first, mobile-friendly concept website. Independent of Atlas of the Cosmos.

## Open it

1. Open this folder in VS Code or Codex.
2. In a terminal here, run `python -m http.server 8000`.
3. Open `http://localhost:8000` in your browser.

The daily lesson, quiz, topic preferences and UI work immediately. NASA news and gallery cards populate from the shared content cache. The initial cache is deliberately empty rather than filled with invented live news.

## Import NASA content

Run `python refresh_content.py` with internet access. It fetches NASA RSS headlines, official article preview images, Image and Video Library thumbnails, and the current Astronomy Picture of the Day into `data/latest.json`. Then refresh the website. Failures retain previously cached data. You can set up a GitHub repository and enable Actions; the supplied workflow refreshes daily. GitHub Pages can host this static site.

### NASA API key

The current sources are public. Space Daily uses `NASA_API_KEY` only as an optional server-side environment variable; it is never printed, stored in `data/latest.json`, or sent to browser code. The new APOD WordPress endpoint does not require a key. If a future NASA source requires a key, set `NASA_API_KEY` locally and add it as a GitHub Actions secret with the same name; never commit it.

## Data sources

- NASA News Release RSS: headlines, dates, links, and summaries.
- NASA article pages: their official social-preview image, when available.
- NASA Image and Video Library: gallery and curated learning imagery, with source links and credited creators.
- NASA APOD WordPress API: `https://science.nasa.gov/wp-json/wp/v2/apod-basic` for the daily image feature. The retiring `api.nasa.gov/planetary/apod` endpoint is not used.

## What is a prototype, not live?

- The newsletter form only checks the email and offers a copy-to-clipboard preference; there is **no live mailing list**.
- User accounts and synced bookmarks are **not implemented**.
- Topic selections are stored locally in the browser; personalised feeds are **not yet implemented**.
- No analytics/tracking is installed.
- The illustrated hero and Moon are CSS art, not NASA photographs.
- NASA headlines link to their sources; the introductory lunar lesson is editorial sample content.

## Safe next steps

- Set up real email subscription with double opt-in, unsubscribes and a privacy notice.
- Add an editorial review process for NASA news, image credit, rights, source dates, and educational accuracy.
- Add privacy-conscious, consent-aware site analytics only after publishing a suitable policy.
- Use a shared backend/cache when adding more sources; do not put secret API keys in public client code.
- For production, choose your domain, site licensing, official contact email and terms; do not imply NASA endorsement.

Sources: https://api.nasa.gov/ · https://www.nasa.gov/rss-feeds/ · https://images.nasa.gov/ · https://www.nasa.gov/nasa-brand-center/images-and-media/
