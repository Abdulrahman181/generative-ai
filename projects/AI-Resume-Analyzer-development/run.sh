#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required. Set PYTHON_BIN to your Python executable." >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating the local virtual environment..."
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  ADMIN_PASSWORD="$(python -c 'import secrets; print("Admin-" + secrets.token_urlsafe(18) + "!A1")')"
  cat > .env <<EOF
# Generated once by run.sh for local development. Do not commit this file.
SECRET_KEY=$SECRET_KEY
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=$ADMIN_PASSWORD
DATABASE_URL=sqlite:///./resume_analyzer.db
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://127.0.0.1:$PORT,http://localhost:$PORT
GROQ_API_KEY=
HF_TOKEN=
EOF
  echo
  echo "Created .env with a new local administrator account."
  echo "Administrator username: admin"
  echo "Administrator email: admin@example.com"
  echo "Administrator password: $ADMIN_PASSWORD"
  echo "Save these credentials; .env is ignored by Git."
  echo
fi

echo "Starting AI Resume Analyzer at http://$HOST:$PORT/"
exec python -m uvicorn main:app --host "$HOST" --port "$PORT"
