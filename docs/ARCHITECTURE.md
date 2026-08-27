# OSIRIS Mimari Dokümanı

Bu doküman, OSIRIS platformunun yüksek seviye mimarisini ve modül sorumluluklarını özetler.
Detaylı teknik plan için bkz. [OSIRIS_Technical_Document.md](OSIRIS_Technical_Document.md).

## Katmanlar

```
┌────────────────────────────────────────────────────────────┐
│ Arayüz Katmanı                                             │
│  Qt6 Desktop · Tauri/Electron · Web UI · CLI · REST API    │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Çekirdek Katmanı (osiris-core, C++)                        │
│  Koordinasyon · Zamanlama · IPC · API Gateway              │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Veri Katmanı                                               │
│  Collector Manager → Plugin'ler → Pipeline → Storage       │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Analiz Katmanı                                             │
│  Query · Graph · Alert · Report                            │
└────────────────────────────────────────────────────────────┘
```

## Veri Akışı

1. **Toplama** — Collector Manager, zamanlanmış plugin'leri çalıştırır.
2. **Kuyruk** — Ham veri Redis kuyruğuna yazılır (`osiris:raw_items`).
3. **İşleme** — Pipeline temizler, dil tespiti yapar, varlık çıkarır, embedding üretir.
4. **Depolama** — İşlenmiş veri PostgreSQL'e yazılır (items, entities, relations).
5. **Analiz** — Query/Graph/Alert/Report katmanları veriyi tüketir.
6. **Sunum** — Arayüzler REST API üzerinden sonuçları gösterir.

## Modül Sorumlulukları

| Modül | Sorumluluk |
|-------|-----------|
| `osiris-core` | Merkezi koordinatör, plugin yaşam döngüsü, zamanlama |
| `osiris-collector` | Plugin yükleme, görev çalıştırma, kuyruğa iletme |
| `osiris-pipeline` | Temizleme, NER, sınıflandırma, embedding, depolama |
| `osiris-query` | Tam metin + semantik arama |
| `osiris-graph` | Varlık ilişki grafı, merkezilik, kümeleme |
| `osiris-alert` | Kayıtlı sorgu izleme, uyarı üretme |
| `osiris-report` | Markdown/JSON/CSV rapor üretimi |
| `osiris-api` | REST API sunucusu |
| `osiris-cli` | Komut satırı arayüzü |
| `osiris-web-ui` | Tarayıcı tabanlı arayüz |

## Güvenlik Modeli

- Tüm dış bağlantılar proxy/VPN/Tor üzerinden yapılabilir (plugin `proxy_config`).
- Kimlik bilgileri Hashicorp Vault'ta şifreli saklanır.
- Denetim logları append-only ve hash zincirlidir (`audit_logs`).
- API erişimi JWT ile korunur.
