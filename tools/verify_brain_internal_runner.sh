#!/usr/bin/env bash
set -euo pipefail

REPO="${BRAIN_GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
EXPECTED=(brain-internal linux x64 qemu windows-real-boot self-hosted)

command -v gh >/dev/null || { echo "MISSING:gh"; exit 2; }
command -v jq >/dev/null || { echo "MISSING:jq"; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "GITHUB_AUTH_REQUIRED"; exit 3; }

json="$(gh api "/repos/$REPO/actions/runners?per_page=100")"
runner="$(printf '%s' "$json" | jq -c '
  .runners[]
  | select(.status=="online")
  | select(([.labels[].name] | map(ascii_downcase)) as $l
      | ["brain-internal","linux","x64","qemu","windows-real-boot","self-hosted"]
      | all(. as $x | $l | index($x) != null))
  | {id,name,status,busy,labels:[.labels[].name]}
' | head -n1)"

if [ -z "$runner" ]; then
  echo "BRAIN_INTERNAL_RUNNER=NOT_VERIFIED"
  echo "No ONLINE runner with the required Brain labels was found."
  exit 10
fi

printf '%s
' "$runner"
echo "BRAIN_INTERNAL_RUNNER=VERIFIED"
