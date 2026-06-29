#!/usr/bin/env bash
# Bootstrap a local .env file with generated secrets for Docker services.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
EXAMPLE_FILE="${ROOT_DIR}/.env.example"

if [[ -f "${ENV_FILE}" ]]; then
  echo ".env already exists — skipping bootstrap."
  exit 0
fi

cp "${EXAMPLE_FILE}" "${ENV_FILE}"

FERNET_KEY="$(python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
REDASH_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
REDASH_COOKIE="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

replace() {
  local placeholder="$1"
  local value="$2"
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|${placeholder}|${value}|" "${ENV_FILE}"
  else
    sed -i "s|${placeholder}|${value}|" "${ENV_FILE}"
  fi
}

replace "generate_a_fernet_key_here" "${FERNET_KEY}"
replace "generate_a_redash_secret_key_here" "${REDASH_SECRET}"
replace "generate_a_redash_cookie_secret_here" "${REDASH_COOKIE}"

echo "Created ${ENV_FILE} with generated secrets."
echo "Review credentials before sharing or committing."
