#!/bin/sh
# Thorsten Kokoro HA Add-on startup: HTTP 8000 + Wyoming 10200 in parallel.
#
# RAM NOTE: http_server.py and wyoming_bridge each load the Kokoro checkpoint
# in their own process (double model loading, ca. 700MB-1GB extra RAM total).
# This is intentional — both services stay independent and restart-safe — at
# the cost of roughly double the model memory vs. a single shared process.
#
# Contract (Dockerfile): ENTRYPOINT ./run.sh, HEALTHCHECK curl localhost:$PORT/health,
# VOLUME /data/hf-cache, EXPOSE 8000 10200.
set -e

# --- HF cache dir ---
HF_CACHE="${HF_HUB_CACHE:-/data/hf-cache}"
mkdir -p "$HF_CACHE"
export HF_HUB_CACHE="$HF_CACHE"
export HF_HOME="$HF_CACHE"

# --- Options from Home Assistant (/data/options.json) with defaults ---
# Defaults (also grep-visible fallback when file is missing):
# KOKORO_EPOCH default 5 (range 1-10)
# SPEED default 1.0
# HF_REPO_ID default Thorsten-Voice/Kokoro
# ENABLE_HTTP default false (HTTP 8000 stays off unless enabled)
OPTIONS_FILE="/data/options.json"
KOKORO_EPOCH="5"
SPEED="1.0"
HF_REPO_ID="Thorsten-Voice/Kokoro"
ENABLE_HTTP="false"
if [ -f "$OPTIONS_FILE" ]; then
  # shellcheck disable=SC2046
  eval "$(python3 -c "
import json
try:
    opts = json.load(open('$OPTIONS_FILE'))
except Exception as exc:
    print('echo \"WARN: could not parse %s: %s\"' % ('$OPTIONS_FILE', exc))
else:
    e = opts.get('KOKORO_EPOCH', 5)
    s = opts.get('SPEED', 1.0)
    r = opts.get('HF_REPO_ID', 'Thorsten-Voice/Kokoro')
    h = opts.get('ENABLE_HTTP', False)
    print('KOKORO_EPOCH=\"%s\"' % e)
    print('SPEED=\"%s\"' % s)
    print('HF_REPO_ID=\"%s\"' % r)
    print('ENABLE_HTTP=\"%s\"' % ('true' if h is True or str(h).lower() == 'true' else 'false'))
")"
else
  echo "No $OPTIONS_FILE found, using defaults: KOKORO_EPOCH=5 SPEED=1.0 HF_REPO_ID=Thorsten-Voice/Kokoro ENABLE_HTTP=false"
fi
# Defaults fallback when options.json is missing keys or empty:
# KOKORO_EPOCH default 5, SPEED default 1.0, HF_REPO_ID default Thorsten-Voice/Kokoro, ENABLE_HTTP default false
: "${KOKORO_EPOCH:=5}"
: "${SPEED:=1.0}"
: "${HF_REPO_ID:=Thorsten-Voice/Kokoro}"
: "${ENABLE_HTTP:=false}"
export KOKORO_EPOCH SPEED HF_REPO_ID ENABLE_HTTP
echo "Options: KOKORO_EPOCH=$KOKORO_EPOCH SPEED=$SPEED HF_REPO_ID=$HF_REPO_ID ENABLE_HTTP=$ENABLE_HTTP HF_CACHE=$HF_CACHE"

PORT="${PORT:-8000}"
export PORT

cleanup() {
  echo "Shutting down..."
  # shellcheck disable=SC2086
  kill $HTTP_PID $WYOMING_PID 2>/dev/null || true
  wait 2>/dev/null || true
}
trap 'cleanup; exit 143' TERM INT
trap 'cleanup' EXIT

HTTP_PID=""
WYOMING_PID=""

# --- Wyoming bridge (always on, auto-discovered, no host port needed) ---
echo "Starting wyoming_bridge on port 10200 ..."
python3 -m wyoming_bridge --uri tcp://0.0.0.0:10200 &
WYOMING_PID=$!
echo "wyoming_bridge PID=$WYOMING_PID port=10200 (uri=tcp://0.0.0.0:10200)"

# --- HTTP server (opt-in via ENABLE_HTTP) ---
if [ "$ENABLE_HTTP" = "true" ]; then
  echo "Starting http_server.py on port 8000 ..."
  python3 http_server.py --port 8000 &
  HTTP_PID=$!
  echo "http_server.py PID=$HTTP_PID port=8000"
else
  echo "HTTP 8000 disabled (ENABLE_HTTP=false)."
fi

# --- Warmup: wait briefly for enabled services (bounded, never blocks forever) ---
if [ -n "$HTTP_PID" ]; then
  echo "Warmup: waiting for http://localhost:8000/health (max ~60s) ..."
  i=0
  while [ "$i" -lt 60 ]; do
    if curl -fs "http://localhost:8000/health" >/dev/null 2>&1; then
      echo "Warmup OK: HTTP 8000 healthy."
      break
    fi
    # Fail fast if either child already died.
    if ! kill -0 "$HTTP_PID" 2>/dev/null; then
      echo "ERROR: http_server.py (8000) exited early." >&2
      wait "$HTTP_PID"
      exit $?
    fi
    if ! kill -0 "$WYOMING_PID" 2>/dev/null; then
      echo "ERROR: wyoming_bridge (10200) exited early." >&2
      wait "$WYOMING_PID"
      exit $?
    fi
    i=$((i + 1))
    sleep 1
  done
  if [ "$i" -ge 60 ]; then
    echo "Warmup timeout: continuing anyway (services run in background)."
  fi
else
  echo "Warmup skipped (HTTP disabled, Wyoming needs no warmup check)."
fi

echo "Services running: HTTP_PID=${HTTP_PID:-off} Wyoming_PID=$WYOMING_PID"
wait
