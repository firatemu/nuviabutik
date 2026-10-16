#!/usr/bin/env bash
# NuviaButik - WSL/local geliştirme ortamı kurulumu
# Ubuntu 22.04+ / Debian tabanlı dağıtımlarda test edildi
set -euo pipefail

# -------- Konfigürasyon --------
REPO_URL="${REPO_URL:-https://github.com/firatemu/nuviabutik.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/projects/nuviabutik}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
SETTINGS_MODULE="${SETTINGS_MODULE:-stoktakip.local}"
PORT="${PORT:-8000}"

log() { printf "\033[1;34m[setup]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m[fail]\033[0m %s\n" "$*"; exit 1; }

# -------- Önkoşullar --------
log "Python ve sistem bağımlılıkları kontrol ediliyor"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    fail "$PYTHON_BIN bulunamadı. 'sudo apt install -y python3 python3-venv python3-pip' çalıştırın."
fi

PY_VERSION="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
log "Python $PY_VERSION algılandı"

if ! "$PYTHON_BIN" -m venv --help >/dev/null 2>&1; then
    warn "venv modülü yok, python3-venv kuruluyor"
    sudo apt-get update -y >/dev/null
    sudo apt-get install -y python3-venv python3-dev >/dev/null
fi

# Pillow için gerekebilecek sistem kütüphaneleri
if ! dpkg -l libjpeg-dev libpng-dev >/dev/null 2>&1; then
    warn "Pillow sistem bağımlılıkları kuruluyor (sudo gerekebilir)"
    sudo apt-get install -y libjpeg-dev libpng-dev zlib1g-dev >/dev/null || \
        warn "Sistem paketleri kurulamadı; Pillow build başarısız olursa tekrar deneyin"
fi

# -------- Repo --------
if [ -d "$PROJECT_DIR/.git" ]; then
    log "Repo zaten var, güncelleniyor: $PROJECT_DIR"
    git -C "$PROJECT_DIR" fetch origin "$REPO_BRANCH"
    git -C "$PROJECT_DIR" reset --hard "origin/$REPO_BRANCH"
else
    log "Repo klonlanıyor: $REPO_URL"
    mkdir -p "$(dirname "$PROJECT_DIR")"
    git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$PROJECT_DIR"
fi

# -------- venv --------
if [ ! -d "$VENV_DIR" ]; then
    log "Sanal ortam oluşturuluyor: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
log "Pip güncelleniyor"
pip install --upgrade pip wheel >/dev/null

log "Bağımlılıklar kuruluyor (requirements.txt)"
pip install -r "$PROJECT_DIR/requirements.txt"

# -------- .env (local) --------
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    log ".env oluşturuluyor (local ayarlar)"
    cat > "$ENV_FILE" <<EOF
# Local / WSL ayarları — bu dosya repoya eklenmez
DJANGO_SETTINGS_MODULE=$SETTINGS_MODULE
DEBUG=True
SECRET_KEY=local-dev-secret-change-me
ALLOWED_HOSTS=*
REDIS_URL=redis://127.0.0.1:6379/1
USE_REDIS_CACHE=False
NUVIABUTIK_DATA_DIR=$HOME/.nuviabutik
EOF
    warn ".env üretim secret'ı içermez; repoya kesinlikle commit etmeyin"
else
    log ".env zaten var, atlanıyor"
fi

# -------- Veritabanı --------
cd "$PROJECT_DIR"
log "Migration uygulanıyor"
export DJANGO_SETTINGS_MODULE="$SETTINGS_MODULE"
python manage.py migrate --noinput

log "Süper kullanıcı oluşturuluyor (admin / admin)"
python manage.py shell <<'PY' || warn "Süper kullanıcı oluşturulamadı (zaten var olabilir)"
from django.contrib.auth import get_user_model
U = get_user_model()
if not U.objects.filter(username='admin').exists():
    u = U.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('OK: admin/admin oluşturuldu')
else:
    print('admin zaten mevcut, atlandı')
PY

log "Statik dosyalar toplanıyor"
python manage.py collectstatic --noinput >/dev/null

# -------- Bilgi --------
cat <<EOF

\033[1;32m✔ Kurulum tamam\033[0m

Çalıştırmak için:
    cd $PROJECT_DIR
    source venv/bin/activate
    export DJANGO_SETTINGS_MODULE=$SETTINGS_MODULE
    python manage.py runserver 0.0.0.0:$PORT

veya tek seferde:
    $VENV_DIR/bin/python $PROJECT_DIR/manage.py runserver 0.0.0.0:$PORT

Giriş: http://127.0.0.1:$PORT/kullanici/login/
Kullanıcı: admin
Parola  : admin

Notlar:
  * Redis kullanılmıyor (LocMem cache). Prod ile aynı kod tabanı.
  * Print agent endpoint'leri localde çalışmaz (sadece sunucuda).
  * Cloudinary / S3 gibi harici servisler kullanılmıyorsa ek ayar gerekmez.
EOF
