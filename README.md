# OSIRIS

> **O**pen **S**ource **I**ntelligence **R**esearch & **I**nformation **S**ystem

OSIRIS, çoklu ağlardan (internet, karanlık ağ, P2P, şifreli ağlar) veri toplayan, bu verileri birbirine bağlayan, ilişkilendiren ve analiz eden; tamamen self-host çalışan gelişmiş bir açık kaynak istihbarat (OSINT) platformudur.

Sistem, bir VDS (Virtual Dedicated Server) üzerinde 7/24 kesintisiz çalışacak şekilde tasarlanmıştır. Tüm bileşenler kullanıcı kontrolündedir; dışarıya veri sızdırmaz, üçüncü taraf bulut servislerine bağımlı değildir.

## Temel Felsefe

- **Gizlilik önce gelir** — Tüm bağlantılar proxy/VPN/Tor üzerinden yapılabilir
- **Modülerlik** — Her veri kaynağı bağımsız bir plugin'dir; çalışan sistemi durdurmadan eklenir/çıkarılır
- **Genişletilebilirlik** — Yeni ağ türleri, protokoller ve analiz yöntemleri kolayca entegre edilebilir
- **Şeffaflık** — Kaynak kodu açık, her işlem loglanır, denetlenebilir

## Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────────────┐
│                        OSIRIS PLATFORM                          │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │  Qt GUI  │   │ Tauri/   │   │   CLI    │   │  REST    │   │
│  │ (Desktop)│   │Electron  │   │ Arayüzü  │   │  API     │   │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   │
│       └──────────────┴──────────────┴──────────────┘          │
│                              │                                  │
│                    ┌─────────▼─────────┐                       │
│                    │   API Gateway /   │                        │
│                    │   Core Engine     │  (C++ / Rust)          │
│                    └─────────┬─────────┘                       │
│              ┌───────────────┼───────────────┐                 │
│              │               │               │                  │
│    ┌─────────▼───┐  ┌────────▼──────┐  ┌────▼────────────┐    │
│    │  Collector  │  │   Processing  │  │   Storage       │    │
│    │  Manager   │  │   Pipeline    │  │   Layer         │    │
│    │  (Python)  │  │   (Python/C++)│  │   (PostgreSQL)  │    │
│    └──────┬──────┘  └───────────────┘  └─────────────────┘    │
│           │                                                      │
│    ┌──────▼──────────────────────────────────────────────┐      │
│    │              Plugin Koleksiyonu                      │      │
│    │  [WWW] [Tor] [I2P] [RSS] [API] [P2P] [Shodan] ...  │      │
│    └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Modüller

| Modül | Dil | Rol |
|-------|-----|-----|
| `osiris-core` | C++20 | Merkezi koordinatör, görev zamanlama, IPC, REST API |
| `osiris-collector` | Python | Veri toplama plugin'lerini yönetir |
| `osiris-pipeline` | Python | Temizleme, NER, sınıflandırma, embedding, ilişkilendirme |
| `osiris-query` | C++/Python | Full-text + semantik arama |
| `osiris-graph` | Python | Varlık ilişki grafı analizi |
| `osiris-alert` | Python | Uyarı ve anomali tespiti |
| `osiris-report` | Python | Rapor üretimi ve dışa aktarım |
| `osiris-api` | Python | REST API sunucusu |
| `osiris-cli` | Python | Komut satırı arayüzü |
| `osiris-web-ui` | React/TS | Tarayıcı tabanlı arayüz |

## Teknoloji Stack'i

- **Diller:** C++20, Python 3.11+, Rust (opsiyonel), TypeScript
- **Veritabanı:** PostgreSQL 16 (+ pgvector, TimescaleDB), Redis, MinIO
- **Arayüz:** Qt6, Tauri, Electron, React + Tailwind
- **Otomasyon:** N8N, FreshRSS, Celery + Redis, APScheduler
- **Güvenlik:** OpenSSL, GnuPG, libsodium, Hashicorp Vault, WireGuard
- **Dağıtım:** Docker, Docker Compose, Systemd, Nginx/Caddy

## Yol Haritası

| Faz | Kapsam | Süre |
|-----|--------|------|
| **Faz 1** | Temel Altyapı: Core Engine, DB şeması, ilk 3 plugin, pipeline, CLI | Ay 1-3 |
| **Faz 2** | Ağ Genişlemesi: Tor, I2P, IRC/Matrix, Shodan, DNS/WHOIS, Web UI | Ay 4-6 |
| **Faz 3** | Analiz Katmanı: Graf, semantik arama, uyarı, rapor | Ay 7-9 |
| **Faz 4** | Otomasyon & Olgunlaşma: N8N, blockchain, SDR, Tauri, testler | Ay 10-12 |

## Hızlı Başlangıç

```bash
# Tüm servisleri başlat (PostgreSQL, Redis, MinIO, N8N, FreshRSS, Nginx)
docker compose up -d

# CLI aracını kur
pip install -e ./osiris-cli

# CLI kullanımı
osiris --help
```

## Dokümantasyon

Detaylı mimari ve planlama dokümanı: [docs/OSIRIS_Technical_Document.md](docs/OSIRIS_Technical_Document.md)

## Lisans

GNU General Public License v3.0 — bkz. [LICENSE](LICENSE)
