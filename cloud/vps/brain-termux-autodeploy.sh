#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_DEFAULT="https://github.com/omarenserat1980/MySimpleProject.git"
HOST="${BRAIN_VPS_HOST:-}"
USER="${BRAIN_VPS_USER:-root}"
PORT="${BRAIN_SSH_PORT:-22}"
KEY="${BRAIN_SSH_KEY:-}"
APP_DIR="${BRAIN_APP_DIR:-/opt/brain-cloud}"
REPO="${BRAIN_REPO:-$REPO_DEFAULT}"
RETRIES="${BRAIN_DEPLOY_RETRIES:-3}"

log(){ printf '\n[Brain-Termux] %s\n' "$*"; }
die(){ printf '\n[Brain-Termux][ERROR] %s\n' "$*" >&2; exit 1; }

command -v ssh >/dev/null 2>&1 || die "OpenSSH غير مثبت. نفّذ: pkg update -y && pkg install openssh -y"
command -v curl >/dev/null 2>&1 || die "curl غير مثبت. نفّذ: pkg install curl -y"

if [[ -z "$HOST" ]]; then read -r -p "عنوان VPS (IP أو hostname): " HOST; fi
[[ -n "$HOST" ]] || die "لم يتم إدخال عنوان VPS."

SSH_OPTS=(-o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3)
[[ -n "${BRAIN_SSH_OPTS:-}" ]] && read -r -a EXTRA_OPTS <<< "${BRAIN_SSH_OPTS}" && SSH_OPTS+=("${EXTRA_OPTS[@]}")
[[ -n "$KEY" ]] && SSH_OPTS+=(-i "$KEY")
SSH=(ssh "${SSH_OPTS[@]}" -p "$PORT")

log "فحص اتصال SSH إلى $USER@$HOST:$PORT"
"${SSH[@]}" "$USER@$HOST" 'echo BRAIN_SSH_OK' | grep -q BRAIN_SSH_OK || die "تعذر اتصال SSH."

REMOTE_SCRIPT=$(cat <<'REMOTE'
set -euo pipefail
APP_DIR='__APP_DIR__'
REPO='__REPO__'
export DEBIAN_FRONTEND=noninteractive
as_root() {
  if [[ "${EUID}" -eq 0 ]]; then "$@";
  elif command -v sudo >/dev/null 2>&1; then sudo "$@";
  else echo "يجب استخدام root أو تثبيت sudo."; exit 20; fi
}
echo "[1/7] تثبيت المتطلبات"
as_root apt-get update -y
as_root apt-get install -y ca-certificates curl git openssl
echo "[2/7] تثبيت Docker/Compose"
if ! command -v docker >/dev/null 2>&1; then curl -fsSL https://get.docker.com | as_root sh; fi
as_root systemctl enable --now docker
if ! docker compose version >/dev/null 2>&1; then as_root apt-get install -y docker-compose-plugin; fi
echo "[3/7] تجهيز المستودع"
as_root mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/.git" ]]; then as_root git clone "$REPO" "$APP_DIR";
else as_root git -C "$APP_DIR" fetch origin main; as_root git -C "$APP_DIR" reset --hard origin/main; fi
echo "[4/7] تهيئة Brain"
cd "$APP_DIR/cloud"
if [[ ! -f .env ]]; then as_root cp .env.production.example .env; as_root chmod 600 .env; fi
TOKEN=$(as_root awk -F= '/^BRAIN_CONTROL_TOKEN=/{print substr($0,index($0,"=")+1)}' .env || true)
if [[ -z "$TOKEN" || "$TOKEN" == "replace-with-a-long-random-secret" ]]; then
  TOKEN=$(openssl rand -hex 32)
  as_root sed -i "s#^BRAIN_CONTROL_TOKEN=.*#BRAIN_CONTROL_TOKEN=$TOKEN#" .env
  as_root chmod 600 .env
  echo "تم إنشاء BRAIN_CONTROL_TOKEN آمنًا (لن يتم طباعته)."
fi
echo "[5/7] تشغيل Brain Cloud"
if ! as_root docker compose -f docker-compose.production.yml pull; then
  echo "GHCR غير متاح؛ سيتم البناء محليًا."
  as_root docker compose -f docker-compose.production.yml build --pull
fi
as_root docker compose -f docker-compose.production.yml up -d
as_root docker compose -f docker-compose.production.yml ps
echo "[6/7] انتظار الصحة"
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8000/readyz >/dev/null 2>&1; then
    echo "BRAIN_DEPLOY_OK"; break
  fi
  if [[ "$i" -eq 30 ]]; then
    as_root docker compose -f docker-compose.production.yml logs --tail=120
    exit 30
  fi
  sleep 3
done
echo "[7/7] الفحص النهائي"
as_root docker compose -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:8000/healthz
printf '\nBrain Cloud جاهز. منفذ 8000 مربوط إلى localhost فقط.\n'
REMOTE
)
REMOTE_SCRIPT="${REMOTE_SCRIPT//__APP_DIR__/$APP_DIR}"
REMOTE_SCRIPT="${REMOTE_SCRIPT//__REPO__/$REPO}"

for attempt in $(seq 1 "$RETRIES"); do
  log "بدء النشر — المحاولة $attempt/$RETRIES"
  if printf '%s\n' "$REMOTE_SCRIPT" | "${SSH[@]}" "$USER@$HOST" 'bash -s'; then
    log "اكتمل النشر والفحص بنجاح."
    exit 0
  fi
  [[ "$attempt" -lt "$RETRIES" ]] && { log "إعادة المحاولة بعد 5 ثوانٍ."; sleep 5; }
done
die "فشل النشر بعد $RETRIES محاولات. لم يتم عرض أي أسرار."
