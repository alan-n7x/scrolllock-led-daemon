#!/usr/bin/env bash
set -euo pipefail

gpg_args=(
    --batch
    --yes
    --pinentry-mode loopback
    --passphrase "${GPG_PASSPHRASE:-}"
)

exec gpg "${gpg_args[@]}" "$@"
