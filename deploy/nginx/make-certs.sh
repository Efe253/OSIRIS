#!/bin/sh
# OSIRIS Nginx — self-signed bootstrap sertifikası üretir.
# Taze kurulumda nginx cert dosyaları olmadan ayağa kalkamaz; bu script
# ilk kurulumda BİR KEZ çalıştırılır:
#   ./deploy/nginx/make-certs.sh
# Gerçek alan adı + Let's Encrypt'e geçince sertifikaları değiştirip
# `docker compose up -d --force-recreate --no-deps nginx` yapın.
set -eu
DIR="$(dirname "$0")/certs"
mkdir -p "$DIR"
if [ -f "$DIR/osiris.local.crt" ]; then
  echo "mevcut sertifika korunuyor: $DIR/osiris.local.crt"
  exit 0
fi
openssl req -x509 -newkey rsa:2048 -days 825 -nodes \
  -keyout "$DIR/osiris.local.key" -out "$DIR/osiris.local.crt" \
  -subj "/CN=osiris.local" \
  -addext "subjectAltName=DNS:osiris.local,DNS:localhost,IP:127.0.0.1"
chmod 600 "$DIR/osiris.local.key"
echo "uretildi: $DIR/osiris.local.{crt,key}"
