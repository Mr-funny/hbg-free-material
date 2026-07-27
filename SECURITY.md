# Security

## API keys

Never commit `.env` or paste provider keys into issues, logs, screenshots, manifests, or AI prompts. Use environment variables or a local `.env` copied from `.env.example`.

If a key is exposed, revoke it at the provider immediately and replace it with a new one.

## Download safety

The CLI accepts only HTTP(S) download URLs, rejects private/local IP literals, validates returned media types, writes through temporary `.part` files, and enforces configurable size limits.

The optional music proxy binds to `127.0.0.1` by default and accepts only HTTPS URLs under `cdn.pixabay.com/audio/`.
