"""Free LLM providers through their OpenAI-compatible endpoints (plain HTTP, no SDK).

Pick one with LLM_PROVIDER = gemini | groq | ollama.
If unset, the first provider whose API key is set gets used.
"""
import os
import time

import requests

PROVIDERS = {
    # Google AI Studio free tier. Big model, best at recognising songs, including regional/Indian music.
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3.8-flash",
        "delay": 6.5,   # stays under the free-tier requests-per-minute limit
        "batch": 50,    # free tier is only ~20 requests/day, so send big batches
    },
    # Groq free tier. Very fast, no card needed.
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
        "delay": 12,    # free tier has a tokens-per-minute cap
        "batch": 20,    # one request must fit in the 8k tokens-per-minute cap
    },
    # Runs locally on your Mac. Fully offline and unlimited, but smaller models know fewer songs.
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "key_env": None,
        "model": "qwen2.5:7b",
        "delay": 0,
    },
}


def active_provider():
    name = os.environ.get("LLM_PROVIDER", "").lower().strip()
    if not name:
        for n, p in PROVIDERS.items():
            if p["key_env"] and os.environ.get(p["key_env"]):
                name = n
                break
    return name if name in PROVIDERS else None


def is_enabled():
    return active_provider() is not None


def describe():
    name = active_provider()
    return f"{name} / {_model(name)}" if name else "none"


def batch_size(default):
    name = active_provider()
    return PROVIDERS[name].get("batch", default) if name else default


def _model(name):
    return os.environ.get("MOOD_LLM_MODEL") or PROVIDERS[name]["model"]


class QuotaExhausted(RuntimeError):
    """The provider's daily quota is used up; retrying today won't help."""


def _retry_delay(r):
    """Seconds the provider asks us to wait, from the header or Gemini's RetryInfo."""
    ra = r.headers.get("retry-after")
    if ra and ra.replace(".", "", 1).isdigit():
        return float(ra)
    try:
        err = r.json()
        err = err[0] if isinstance(err, list) else err
        for d in err.get("error", {}).get("details", []):
            if d.get("retryDelay"):
                return float(d["retryDelay"].rstrip("s"))
    except (ValueError, AttributeError, TypeError):
        pass
    return None


_last_call = 0.0


def complete(system, user, retries=4):
    """Send one chat request and return the reply text."""
    global _last_call
    name = active_provider()
    if not name:
        raise RuntimeError("No LLM provider configured")
    p = PROVIDERS[name]
    headers = {"Content-Type": "application/json"}
    if p["key_env"]:
        key = os.environ.get(p["key_env"])
        if not key:
            raise SystemExit(f"LLM_PROVIDER={name} but {p['key_env']} is not set.")
        headers["Authorization"] = f"Bearer {key}"
    body = {
        "model": _model(name),
        "temperature": 0.2,
        "max_tokens": 4000,  # Groq counts this against its 8k tokens-per-minute cap
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }

    for attempt in range(retries):
        wait = p["delay"] - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            r = requests.post(f"{p['base_url']}/chat/completions", json=body,
                              headers=headers, timeout=300)
        except (requests.ConnectionError, requests.Timeout):
            if name == "ollama":
                raise SystemExit("Can't reach Ollama. Is the Ollama app running?")
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 429:
            delay = _retry_delay(r)
            text = r.text.lower()
            # Daily caps (e.g. Gemini free tier: 20 requests/day) -> stop, every retry burns quota
            if "perday" in text or "per day" in text or (delay and delay > 120):
                hours = f" Resets in ~{delay / 3600:.1f}h." if delay else ""
                raise QuotaExhausted(f"{name} daily quota used up.{hours}")
            time.sleep(delay + 1 if delay else 20 * (attempt + 1))
            continue
        if r.status_code >= 500:  # server busy
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code in (401, 403, 404):  # bad key / unknown model: same for every batch
            raise SystemExit(f"{name} error {r.status_code}: {r.text[:300]}\n"
                             f"Check your API key, or set MOOD_LLM_MODEL to a model your account has.")
        if r.status_code != 200:
            raise RuntimeError(f"{name} error {r.status_code}: {r.text[:300]}")
        choice = r.json()["choices"][0]
        if choice.get("finish_reason") == "length":
            raise RuntimeError("reply was cut off (max_tokens); try a smaller LLM_BATCH_SIZE")
        return choice["message"]["content"] or ""
    raise RuntimeError(f"{name}: gave up after {retries} retries (rate limit?)")
