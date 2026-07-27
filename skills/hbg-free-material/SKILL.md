---
name: hbg-free-material
description: Search, compare, and download stock images from Pexels, Unsplash, and Pixabay, stock videos from Pexels and Pixabay, and browser-selected Pixabay music through the hbg-free-material CLI. Use when an agent needs licensed stock media candidates, preview URLs, creator attribution, source links, local files, quality selection, or reproducible manifest records without loading an MCP server.
---

# HBG Free Material

Use the installed `hbg-free-material` CLI for every operation. Keep provider keys in the user's environment or a local `.env`; never print, copy, or commit key values. Prefer JSON output so the agent can compare candidates before downloading.

## Check providers

```bash
hbg-free-material providers
```

Pexels and Pixabay support images and videos. Unsplash supports images only. Pixabay music search is browser-assisted because its public API does not expose music search.

## Search images

```bash
hbg-free-material search "Hong Kong cha chaan teng interior" \
  --platform all --per-page 5 --json
```

Compare subject fit, orientation, dimensions, creator, source page, and provider before selecting.

Download a balanced batch:

```bash
hbg-free-material download "steaming beef noodle soup" \
  --platform all --count 3 --output-dir ./downloads/food --json
```

Fetch one selected result while preserving attribution:

```bash
hbg-free-material fetch "DOWNLOAD_URL" --platform pexels --id "PHOTO_ID" \
  --photographer "NAME" --source-url "SOURCE_URL" --alt "DESCRIPTION" \
  --output-dir ./downloads/selected --json
```

For Unsplash, pass `--download-location` from the search result so the required tracking call is made.

## Search videos

```bash
hbg-free-material video search "cat running in a garden" \
  --platform all --per-page 5 --quality hd --json
```

Quality choices:

- `best`: largest available file.
- `hd`: practical HD or Full HD; default.
- `sd`: smaller provider variant when available.
- `small`: smallest available preview variant.

Download from both supported providers:

```bash
hbg-free-material video download "Hong Kong street at night" \
  --platform all --count 2 --quality hd \
  --output-dir ./downloads/videos/hong-kong --json
```

## Pixabay music

Read [references/pixabay-music.md](references/pixabay-music.md) before a music request. Search in a real browser, then download the selected public CDN result:

```bash
hbg-free-material music fetch "CDN_AUDIO_URL" \
  --id "AUDIO_ID" --artist "ARTIST" --source-url "TRACK_PAGE_URL" \
  --title "TITLE" --duration 120 --filename selected-track --json
```

Run `hbg-free-material proxy` only when a downstream player needs an HTTP range-aware localhost URL.

## Delivery rules

- Translate broad Chinese descriptions into concise English search keywords unless exact text or a named place must remain unchanged.
- Search first; do not automatically accept the first result.
- Preserve the adjacent `manifest.json` with creator, source page, and provider license URL.
- Never claim a provider license covers every possible use. Advise checking the asset page for publication-sensitive work.
- Render downloaded media in chat when the user asks to see or play it, and provide the absolute saved path.
- Use image or video generation skills when the user asks to create or edit media rather than retrieve stock media.
