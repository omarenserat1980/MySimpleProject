#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="omarenserat1980/MySimpleProject"
WORK="$HOME/.brain/android-executor-install"
PACKAGE="com.electronicbrain.androidexecutor"
mkdir -p "$WORK"

command -v gh >/dev/null 2>&1 || {
  echo "BRAIN_INSTALL_ERROR=GH_CLI_MISSING" >&2
  exit 20
}

RUN_JSON="$(gh run list --repo "$REPO" --workflow brain-android-executor.yml --branch main --limit 10 --json databaseId,status,conclusion,headSha --jq '[.[] | select(.status=="completed" and .conclusion=="success")][0]')"
RUN_ID="$(printf '%s' "$RUN_JSON" | sed -n 's/.*"databaseId":\([0-9]*\).*/\1/p')"
HEAD_SHA="$(printf '%s' "$RUN_JSON" | sed -n 's/.*"headSha":"\([^"]*\)".*/\1/p')"

if [ -z "$RUN_ID" ] || [ -z "$HEAD_SHA" ]; then
  echo "BRAIN_INSTALL_ERROR=NO_SUCCESSFUL_EXECUTOR_BUILD" >&2
  exit 21
fi

rm -rf "$WORK/artifact" "$WORK/apk"
mkdir -p "$WORK/artifact" "$WORK/apk"

gh run download "$RUN_ID" --repo "$REPO" --name electronic-brain-android-executor-debug --dir "$WORK/artifact"

APK="$(find "$WORK/artifact" -type f -name 'app-debug.apk' -print -quit)"
if [ -z "$APK" ]; then
  echo "BRAIN_INSTALL_ERROR=APK_MISSING_FROM_ARTIFACT" >&2
  exit 22
fi

cp "$APK" "$WORK/apk/app-debug.apk"
APK_SHA="$(sha256sum "$WORK/apk/app-debug.apk" | awk '{print $1}')"

echo "BRAIN_EXECUTOR_BUILD_RUN=$RUN_ID"
echo "BRAIN_EXECUTOR_HEAD_SHA=$HEAD_SHA"
echo "BRAIN_EXECUTOR_APK_SHA256=$APK_SHA"
echo "BRAIN_EXECUTOR_APK=$WORK/apk/app-debug.apk"

if command -v termux-open >/dev/null 2>&1; then
  termux-open "$WORK/apk/app-debug.apk" || true
else
  echo "BRAIN_INSTALL_ERROR=TERMUX_OPEN_MISSING" >&2
  exit 23
fi

echo "BRAIN_INSTALL_ACTION=ANDROID_PACKAGE_INSTALLER"
echo "BRAIN_INSTALL_NOTE=Complete the Android installation prompt; Android does not permit silent APK installation from an ordinary Termux process."
