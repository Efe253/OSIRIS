# Username Search Plugin'i

Maigret tarzı kullanıcı adı taraması: `sites.json` DB'sindeki profil
URL'lerini yoklar, bulunan profilleri öğe olarak döndürür.

## Kullanım

```bash
osiris collect username-search --config '{"username":"ornek","tags":["dev"],"max_sites":50}'
```

## Binlerce site (Maigret DB)

Gömülü DB ~60 popüler site içerir. Tam Maigret veritabanı için:

```bash
# Maigret reposundan güncel DB'yi indirin
curl -sL https://raw.githubusercontent.com/soxoj/maigret/main/maigret/resources/data.json -o /tmp/maigret-db.json

osiris collect username-search --config '{"username":"ornek","sites_db":"/tmp/maigret-db.json","max_sites":500}'
```

Desteklenen `checkType` değerleri: `status_code`, `message`
(`presenceStrs`/`absenceStrs`), `response_url`. Bilinmeyen türler atlanır.

## Notlar

- Tüm istekler `osiris.security.fetch_url` üzerinden gider (SSRF korumalı,
  yönlendirme-denetimli, gövde tavanlı).
- Erişilemeyen siteler "bilinmiyor" sayılıp atlanır; tek site hatası
  taramayı durdurmaz.
- Kibarlık: varsayılan 10 paralel işçi, site başına 15 sn zaman aşımı.
  Hedefe yüklenmemek için `workers`/`timeout` değerlerini makul tutun.
