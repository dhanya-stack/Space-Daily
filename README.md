# Space Daily — starter website

A separate, static-first, mobile-friendly concept website. Independent of Atlas of the Cosmos.

## Open it

1. Open this folder in VS Code or Codex.
2. In a terminal here, run `python -m http.server 8000`.
3. Open `http://localhost:8000` in your browser.

The daily lesson, quiz, topic preferences and UI work immediately. NASA news and gallery cards populate from the shared content cache. The initial cache is deliberately empty rather than filled with invented live news.

## Import NASA content

Run `python refresh_content.py` with internet access. It fetches NASA's RSS news headlines and Image and Video Library thumbnails into `data/latest.json`. Then refresh the website. Failures retain previously cached data. You can set up a GitHub repository and enable Actions; the supplied workflow refreshes daily. GitHub Pages can host this static site.

### NASA API key

The current sources (NASA's RSS feed and Image and Video Library search API) are public and do **not** require an API key. `NASA_API_KEY` is therefore intentionally not read, sent to the browser, printed, or included in the workflow. If a future server-side content source requires NASA's API, provide the key as an environment variable locally and as a GitHub Actions secret named `NASA_API_KEY`; do not add it to client-side JavaScript, HTML, `data/latest.json`, or the repository.

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
