# Pixabay Music

Pixabay's public API covers images and videos, not music. Public music pages expose playable CDN URLs, but direct server requests to search pages and bootstrap JSON are protected by Cloudflare. Search with the in-app Browser; never reuse browser cookies, bypass Turnstile, or automate a challenge.

## Search workflow

1. Read and use the `browser:control-in-app-browser` skill.
2. Navigate to `https://pixabay.com/zh/music/search/<encoded-query>/`.
3. Enable CDP Network capture before navigation when possible.
4. Find the successful `Network.responseReceived` event whose URL matches `https://pixabay.com/bootstrap/*.json` and type is `Fetch`.
5. Read that response with `Network.getResponseBody`, parse JSON, and use `page.results`.
6. Compare several candidates before selecting one.

Normalize each result as follows:

- `id`: `result.id`
- `title`: `result.name`
- `artist`: `result.user.username`
- `duration`: `result.duration`
- `download_url`: `result.sources.src`
- `thumbnail_url`: `result.sources.thumbnailUrl`
- `source_url`: absolute `https://pixabay.com` + `result.href`
- `tags`: `result.alt` or `result.description`
- `content_id`: `result.hasYoutubeContentId`
- `license_url`: `https://pixabay.com/service/license-summary/`

Only accept `download_url` values under `https://cdn.pixabay.com/audio/`. Treat `hasYoutubeContentId` as publication-relevant metadata and mention it when true.

## Download and proxy

Use `music fetch` for a local file and adjacent manifest. Use `music proxy-url` when another local tool needs streaming or range requests. The proxy is intentionally download-only; do not add a generic URL forwarder or a server-side Pixabay search scraper.
