# Deploying the assistant API (Hostinger KVM 2, 2 vCPU / 8 GB)

The stack: **Ollama** (qwen2.5:7b) + **API** (FastAPI wrapper around `GraphRagEngine`) + **Caddy**
(TLS, security headers), managed by Docker Compose. The frontend stays on GitHub Pages and calls
`https://$DOMAIN/chat`; the chatbot's built-in local mode is the fallback whenever this API is down.

## Memory reality (read first)

Peak usage exceeds 8 GB by design: Ollama holds ~5.3 GB and the API container ~4–4.5 GB
(e5-large-v2 embedder + bge-reranker-v2-m3 + embedded Weaviate). A 4 GB swapfile absorbs the
overshoot — idle API model pages swap out during generation. Cost: a few seconds of swap-in per
request phase, not answer quality. **Do not skip the swap step.**

If you later want to fit fully in RAM, the levers (both invalidate current eval numbers — re-run
the harness first):
- `GEMPRF_ASSISTANT_EMBEDDING_MODEL=intfloat/e5-base-v2` (saves ~0.9 GB; **requires wiping
  `/data/weaviate` to re-ingest** — embedding dimensions change)
- `GEMPRF_ASSISTANT_RERANKER_MODEL=BAAI/bge-reranker-base` (saves ~1 GB)

## One-time setup

```bash
# 1. Swap (4 GB)
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# 2. Docker (if not present)
curl -fsSL https://get.docker.com | sh

# 3. Firewall: only SSH + HTTP/HTTPS (also mirror this in Hostinger's panel firewall)
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable

# 4. Code — submodules carry part of the corpus, --recurse-submodules is required
git clone --recurse-submodules <repo-url> gemprf-assistant
cd gemprf-assistant/deploy
cp .env.example .env   # then edit: set DOMAIN

# 5. DNS: create an A record for $DOMAIN -> this VPS's IP before starting
#    (Caddy needs it resolvable to obtain the Let's Encrypt certificate)

# 6. Launch
docker compose up -d --build
```

## First boot (expect ~15–30 min, one-time)

- `ollama-init` downloads the model (~4.7 GB)
- the API container downloads the embedder + reranker (~3.5 GB) into the `apidata` volume,
  then ingests the corpus (embedding on 2 vCPU takes a few minutes)
- watch with `docker compose logs -f api` until "engine ready"

## Smoke test

```bash
curl -s https://$DOMAIN/healthz            # {"ok":true} — process up
curl -s https://$DOMAIN/readyz             # 503 while ingesting, then {"ok":true,...}
curl -s https://$DOMAIN/chat -H 'content-type: application/json' \
  -d '{"question":"What does the sigma parameter control?"}' | python3 -m json.tool
```

Expect 20–60 s for an uncached answer on this hardware; repeats of the same question return
instantly from the cache.

## API contract

`POST /chat` → `{"question": str (≤600 chars), "history": [{"question","answer"}] (≤8 turns)}`
Returns `{"answer","status","citations","cached","elapsed_s"}`.
Errors: 422 invalid input · 429 per-IP rate limit (10/min) · 503 queue full (8 deep) / engine
loading · 504 generation timeout (180 s). Knobs: `GEMPRF_ASSISTANT_API_{QUEUE_MAX,TIMEOUT_S,CACHE_SIZE,RATE_PER_MIN,CORS}`.

## Operations

- **Monitoring:** point a free UptimeRobot HTTP check at `https://$DOMAIN/readyz`.
- **Logs:** `docker compose logs -f api` — logs question *hashes*, never content.
- **Update:** `git pull --recurse-submodules && docker compose up -d --build`. The Weaviate
  index and models persist in volumes; corpus changes require `docker volume rm` of nothing —
  re-ingest only when the corpus files change (wipe `/data/weaviate` via
  `docker compose exec api rm -rf /data/weaviate` then restart).
- **Rollback:** `git checkout <previous-tag> && docker compose up -d --build`.
- **Privacy:** once the frontend points here, user questions leave the browser. Update the
  site's privacy policy accordingly (questions processed transiently, not stored; only hashed
  identifiers in logs).

## Frontend wiring

In `chatbot.js`, replace the Groq call in `getAPIResponse()` with:

```js
const response = await fetch('https://<DOMAIN>/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question: userMessage, history: this.recentTurns ?? [] }),
});
if (!response.ok) throw new Error(`API ${response.status}`);  // falls back to local mode
const data = await response.json();
```

Keep the existing local-knowledge-base path as the catch-handler fallback, and surface a
"thinking (up to a minute)…" indicator — generation on this VPS is slow by design.
