#!/data/data/com.termux/files/usr/bin/bash
set -eu

MINER="$HOME/cpuminer-publicpool/minerd"
if [ ! -x "$MINER" ]; then
  echo "ERROR: minerd not found at $MINER" >&2
  exit 1
fi

read -r -p 'Enter your own public Bitcoin receiving address (bc1...): ' BTC_ADDRESS
case "$BTC_ADDRESS" in
  bc1*) ;;
  *) echo 'ERROR: expected your own Bitcoin address starting with bc1.' >&2; exit 2 ;;
esac
case "$BTC_ADDRESS" in
  *[!a-zA-Z0-9]*) echo 'ERROR: address contains unexpected characters.' >&2; exit 2 ;;
esac

WORKER_NAME="${BRAIN_MINING_WORKER_NAME:-Realme01}"
case "$WORKER_NAME" in
  ''|*[!a-zA-Z0-9_-]*)
    echo 'ERROR: worker name must contain only letters, numbers, underscore, or hyphen.' >&2
    exit 3
    ;;
esac

printf '\nConfigured Public Pool worker label: %s\n' "$WORKER_NAME"
printf 'Pool mode: PPLNS TLS; miner threads: 1\n'
printf 'This script starts mining only when explicitly launched.\n'
exec "$MINER" --algo=sha256d --url=stratum+tcps://public-pool.io:14333 --user="$BTC_ADDRESS.$WORKER_NAME" --pass=x --threads=1 --retry-pause=10
