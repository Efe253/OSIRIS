# OSIRIS Nginx — TLS notları

- `:80` düz HTTP (LAN/kurulum), `:8443` TLS ile aynı içeriği sunar.
- Sertifika: `certs/` (self-signed, CN=osiris.local, 825 gün). Dosyalar
  git-dışıdır (`*.crt/*.key` ignore'lu) — repoya işlenmez.
- Yenileme: `openssl req -x509 -newkey rsa:2048 -days 825 -nodes ...`
  ardından `docker compose up -d --force-recreate nginx`.
- Gerçek alan adı + Let's Encrypt'e geçince: compose'da `8443:8443`
  yerine `443:8443` yazın, `server_name` güncelleyin, Caddy/başka
  proxy'deki 443 çakışmasını çözün.
