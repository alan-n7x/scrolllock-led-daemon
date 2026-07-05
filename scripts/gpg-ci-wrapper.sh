#!/usr/bin/env bash
set -euo pipefail

gpg_args=(--batch --yes --pinentry-mode loopback)

if [[ -n "${GPG_PASSPHRASE:-}" ]]; then
    gpg_args+=(--passphrase "$GPG_PASSPHRASE")
fi

exec gpg "${gpg_args[@]}" "$@"
