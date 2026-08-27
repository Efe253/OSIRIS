# OSIRIS
## Açık Kaynak İstihbarat (OSINT) Platformu — Detaylı Teknik Doküman

> **O**pen **S**ource **I**ntelligence **R**esearch & **I**nformation **S**ystem  
> Sürüm: 0.1 — Mimari & Planlama Dokümanı  
> Durum: Tasarım Aşaması

---

## İçindekiler

1. [Proje Özeti](#1-proje-özeti)
2. [Temel Özellikler](#2-temel-özellikler)
3. [Sistem Mimarisi](#3-sistem-mimarisi)
4. [Teknoloji Stack'i](#4-teknoloji-stacki)
5. [Modüller ve Bileşenler](#5-modüller-ve-bileşenler)
6. [Desteklenen Ağ ve Protokoller](#6-desteklenen-ağ-ve-protokoller)
7. [Kaynak Yönetim Sistemi](#7-kaynak-yönetim-sistemi)
8. [Veri Akışı](#8-veri-akışı)
9. [Veritabanı Tasarımı](#9-veritabanı-tasarımı)
10. [Güvenlik ve Gizlilik](#10-güvenlik-ve-gizlilik)
11. [Self-Host Altyapı Gereksinimleri](#11-self-host-altyapı-gereksinimleri)
12. [Plugin Mimarisi](#12-plugin-mimarisi)
13. [Arayüz Katmanları](#13-arayüz-katmanları)
14. [Otomasyon ve İş Akışları](#14-otomasyon-ve-iş-akışları)
15. [Yol Haritası](#15-yol-haritası)

---

## 1. Proje Özeti

OSIRIS, çoklu ağlardan (internet, karanlık ağ, P2P, şifreli ağlar) veri toplayan, bu verileri birbirine bağlayan, ilişkilendiren ve analiz eden; tamamen self-host çalışan gelişmiş bir açık kaynak istihbarat (OSINT) platformudur.

Sistem, bir VDS (Virtual Dedicated Server) üzerinde 7/24 kesintisiz çalışacak şekilde tasarlanmıştır. Tüm bileşenler kullanıcı kontrolündedir; dışarıya veri sızdırmaz, üçüncü taraf bulut servislerine bağımlı değildir.

### Temel Felsefe

- **Gizlilik önce gelir** — Tüm bağlantılar proxy/VPN/Tor üzerinden yapılabilir
- **Modülerlik** — Her veri kaynağı bağımsız bir plugin'dir; çalışan sistemi durdurmadan eklenir/çıkarılır
- **Genişletilebilirlik** — Yeni ağ türleri, protokoller ve analiz yöntemleri kolayca entegre edilebilir
- **Şeffaflık** — Kaynak kodu açık, her işlem loglanır, denetlenebilir

---

## 2. Temel Özellikler

### 2.1 Veri Toplama
- Çoklu ağ desteği (WWW, Tor, I2P, Freenet, P2P, Zeronet, vs.)
- Paralel ve zamanlanmış veri çekme (crawler, scraper, feed okuyucu)
- Gerçek zamanlı akış takibi (RSS, Atom, WebSocket, MQTT)
- API entegrasyonu (REST, GraphQL, gRPC)
- Pasif keşif (OSINT teknikleri: WHOIS, DNS, shodan vb.)

### 2.2 Kaynak Yönetimi
- Görsel kaynak ekleme/düzenleme/silme arayüzü
- Kaynak kategorilendirme ve etiketleme
- Kaynak sağlık takibi (uptime, yanıt süresi, başarısızlık sayısı)
- Öncelik sıralaması ve zamanlama (cron tabanlı)
- Kaynak grupları ve koleksiyonlar

### 2.3 Veri İşleme & Analiz
- NLP tabanlı metin analizi (dil tespiti, konu sınıflandırma, duygu analizi)
- Varlık çıkarma (kişi, yer, organizasyon, IP, domain, kripto adresi)
- İlişki grafı (entity graph) oluşturma
- Zaman serisi analizi (olayların kronolojik izlenmesi)
- Görüntü analizi (EXIF verisi, yüz/nesne tanıma opsiyonel)
- Hash ve parmak izi eşleştirme

### 2.4 Arama & Sorgulama
- Tam metin arama (full-text search)
- Gelişmiş filtreler (kaynak türü, tarih aralığı, dil, coğrafya, güven skoru)
- Boolean sorgu desteği (AND, OR, NOT, NEAR)
- Regex tabanlı arama
- Kayıtlı sorgular ve uyarılar (alert sistemi)

### 2.5 Görselleştirme
- İlişki grafı (graf/ağ görselleştirme)
- Zaman çizelgesi (timeline)
- Coğrafi harita üzerinde veri noktaları
- İstatistiksel dashboard (kaynak başına veri hacmi, trendler)
- Heatmap (yoğunluk haritaları)

### 2.6 Raporlama & Dışa Aktarım
- Otomatik rapor üretimi (Markdown, PDF, HTML)
- Veri dışa aktarımı (JSON, CSV, XML, STIX/TAXII — tehdit istihbaratı formatı)
- Paylaşım için şifrelenmiş rapor paketleri
- Zaman damgalı ve imzalı (GPG) kanıt dosyaları

### 2.7 Otomasyon
- N8N tabanlı görsel iş akışı oluşturucu
- Tetikleyici-eylem sistemi (if/then kuralları)
- Webhook desteği (dış sistemlere bildirim)
- Zamanlanmış görevler (cron)
- Akıllı uyarı sistemi (anomali tespiti)

---

## 3. Sistem Mimarisi

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
│                                                                  │
│    ┌───────────────┐    ┌───────────────┐    ┌──────────────┐   │
│    │   N8N         │    │  FreshRSS     │    │  Message     │   │
│    │  Otomasyon    │    │  Feed Engine  │    │  Queue       │   │
│    └───────────────┘    └───────────────┘    │  (Redis /    │   │
│                                              │   RabbitMQ)  │   │
│                                              └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Katman Açıklamaları

| Katman | Rol | Teknoloji |
|--------|-----|-----------|
| **Arayüz** | Kullanıcı ile etkileşim | Qt6, Tauri, Electron |
| **API Gateway** | Tüm bileşenleri birbirine bağlar | C++ / Rust (REST + IPC) |
| **Core Engine** | Görev yönetimi, zamanlama, orkestrasyon | C++ |
| **Collector Manager** | Plugin'leri yönetir, görev kuyruğuna ekler | Python |
| **Processing Pipeline** | Veriyi temizler, dönüştürür, zenginleştirir | Python + C++ |
| **Storage Layer** | Kalıcı veri saklama | PostgreSQL + Redis |
| **Otomasyon** | İş akışları ve tetikleyiciler | N8N |
| **Feed Engine** | RSS/Atom yönetimi | FreshRSS |
| **Message Queue** | Bileşenler arası asenkron iletişim | Redis / RabbitMQ |

---

## 4. Teknoloji Stack'i

### 4.1 Sistem Dilleri

| Dil | Kullanım Alanı | Gerekçe |
|-----|----------------|---------|
| **C++** (C++20) | Core Engine, yüksek performanslı crawler, native UI | Bellek verimliliği, hız, sistem erişimi |
| **Python 3.11+** | Plugin'ler, veri işleme, ML, scripting | Hız gelişimi, kütüphane zenginliği |
| **Rust** *(opsiyonel)* | Güvenlik kritik modüller, parser'lar | Bellek güvenliği, C++ kadar hızlı |
| **SQL** | Veritabanı sorguları | — |
| **JavaScript/TypeScript** | Electron/Tauri web katmanı | — |

### 4.2 Veritabanı & Depolama

| Teknoloji | Kullanım |
|-----------|----------|
| **PostgreSQL 16** | Ana ilişkisel veritabanı (tüm toplanan veri) |
| **pgvector** | Vektör gömmeleri (embedding) — semantik arama için PostgreSQL eklentisi |
| **Redis** | Önbellek, oturum yönetimi, mesaj kuyruğu |
| **TimescaleDB** | Zaman serisi verileri (PostgreSQL eklentisi) |
| **Elasticsearch** *(opsiyonel)* | Büyük ölçekli tam metin arama |
| **MinIO** | Yerel S3-uyumlu nesne depolama (medya, dosyalar) |

### 4.3 Arayüz Teknolojileri

| Teknoloji | Platform | Kullanım |
|-----------|----------|---------|
| **Qt6** (C++) | Desktop (Linux, Windows, macOS) | Ana masaüstü istemcisi |
| **Tauri** (Rust + Web) | Cross-platform lightweight | Hafif web tabanlı arayüz |
| **Electron** (Node.js + Web) | Cross-platform | Alternatif web arayüzü |
| **Web UI** (React/Vue) | Tarayıcı | Sunucu üzerinden erişim |

### 4.4 Ağ & Bağlantı Kütüphaneleri

| Kütüphane | Dil | Amaç |
|-----------|-----|-------|
| **libcurl** | C/C++ | HTTP/HTTPS, proxy desteği |
| **Stem** | Python | Tor kontrolü (Control Port) |
| **PySocks** | Python | SOCKS4/5 proxy |
| **i2p.socket** | Python | I2P ağı bağlantısı |
| **libtorrent** | C++ | BitTorrent/DHT |
| **libssh2** | C++ | SSH tünelleme |
| **Scapy** | Python | Paket düzeyinde ağ analizi |

### 4.5 Veri İşleme & ML

| Kütüphane | Amaç |
|-----------|-------|
| **spaCy** | NLP, varlık çıkarma (NER) |
| **NLTK** | Doğal dil işleme |
| **langdetect** | Dil tespiti |
| **sentence-transformers** | Semantik benzerlik, embedding |
| **scikit-learn** | Makine öğrenimi, sınıflandırma |
| **NetworkX** | Graf analizi (ilişki ağı) |
| **Pillow / OpenCV** | Görüntü işleme, EXIF analizi |
| **Pandas** | Veri manipülasyonu |
| **Apache Kafka** *(opsiyonel)* | Yüksek hacimli veri akışı |

### 4.6 Otomasyon & Entegrasyon

| Teknoloji | Rol |
|-----------|-----|
| **N8N** (self-hosted) | Görsel iş akışı ve otomasyon motoru |
| **FreshRSS** (self-hosted) | RSS/Atom feed yönetimi ve okuyucu |
| **Apache Airflow** *(opsiyonel)* | Karmaşık pipeline zamanlama |
| **Celery + Redis** | Dağıtık görev kuyruğu |
| **APScheduler** | Python tabanlı zamanlama (cron) |

### 4.7 Güvenlik & Şifreleme

| Teknoloji | Kullanım |
|-----------|---------|
| **OpenSSL / LibreSSL** | TLS/SSL, sertifika yönetimi |
| **GnuPG (GPG)** | Rapor imzalama, şifreli dışa aktarım |
| **libsodium** | Modern şifreleme (NaCl) |
| **Hashicorp Vault** | Sır/API anahtarı yönetimi |
| **WireGuard** | VPN tünelleme |
| **Fail2ban** | Brute-force koruması |

### 4.8 Konteyner & Dağıtım

| Teknoloji | Kullanım |
|-----------|---------|
| **Docker** | Servis konteynerizasyonu |
| **Docker Compose** | Çoklu servis orchestration |
| **Systemd** | Servis yaşam döngüsü yönetimi |
| **Nginx** | Ters proxy, SSL sonlandırma |
| **Caddy** *(alternatif)* | Otomatik HTTPS ile ters proxy |

---

## 5. Modüller ve Bileşenler

### 5.1 Core Engine (`osiris-core`)
- **Dil:** C++20
- **Rol:** Tüm sistemin merkezi koordinatörü
- **Sorumluluklar:**
  - Plugin yaşam döngüsü yönetimi (yükleme, başlatma, durdurma, güncelleme)
  - Görev zamanlama ve kuyruklama
  - Kaynak yönetimi (CPU, bellek, ağ bant genişliği limitleri)
  - IPC (Inter-Process Communication) sunucusu
  - REST API sunucusu (iç ve dış arayüzler için)
  - Log ve izleme altyapısı

### 5.2 Collector Manager (`osiris-collector`)
- **Dil:** Python + C++ (binding)
- **Rol:** Tüm veri toplama plugin'lerini yönetir
- **Sorumluluklar:**
  - Plugin yükleme/kaldırma
  - Paralel koleksiyon görevi başlatma
  - Başarısızlık yönetimi ve yeniden deneme (retry)
  - Hız sınırlama (rate limiting) ve kaynak koruma
  - Toplanan ham veriyi pipeline'a iletme

### 5.3 Processing Pipeline (`osiris-pipeline`)
- **Dil:** Python (+ C++ modüller hız için)
- **Aşamalar:**
  1. **Temizleme:** HTML soyutlama, boşluk normalizasyonu, encoding düzeltme
  2. **Dil Tespiti:** Otomatik dil etiketleme
  3. **Varlık Çıkarma (NER):** Kişi, yer, org, IP, domain, email, kripto adresi
  4. **Sınıflandırma:** Konu, kategori, tehdit türü etiketleme
  5. **Embedding:** Semantik vektör oluşturma (benzerlik arama için)
  6. **İlişkilendirme:** Var olan varlıklarla graf bağlantısı
  7. **Depolama:** PostgreSQL'e yazma

### 5.4 Query Engine (`osiris-query`)
- **Dil:** C++ / Python
- **Özellikler:**
  - Full-text search (PostgreSQL FTS + pgvector semantik arama)
  - Kayıtlı sorgu yönetimi
  - Gerçek zamanlı sorgu (WebSocket)
  - Sorgu şablonları

### 5.5 Graph Engine (`osiris-graph`)
- **Dil:** Python (NetworkX) + C++ (performans)
- **Özellikler:**
  - Varlıklar arası ilişki grafı
  - Merkezi düğüm tespiti (centrality analysis)
  - Kümeleme (community detection)
  - Zaman-ağırlıklı graf analizi
  - Görsel dışa aktarım (GraphML, GEXFi, JSON)

### 5.6 Alert Manager (`osiris-alert`)
- **Dil:** Python
- **Özellikler:**
  - Anahtar kelime eşleştirme uyarıları
  - Anomali tespiti (baseline'dan sapma)
  - Bildirim kanalları: Email, Telegram, Webhook, yerel bildirim
  - Uyarı önceliklendirme ve susturma (mute) kuralları

### 5.7 Report Generator (`osiris-report`)
- **Dil:** Python
- **Çıktı formatları:** Markdown, PDF (WeasyPrint/Pandoc), HTML, JSON, CSV, STIX 2.1

---

## 6. Desteklenen Ağ ve Protokoller

### 6.1 Açık İnternet (WWW)
- HTTP/HTTPS (curl, requests, Playwright)
- WebSocket (gerçek zamanlı veri akışı)
- Web scraping (Playwright, Selenium, BeautifulSoup)
- REST API ve GraphQL
- RSS / Atom feed
- FTP / SFTP
- SMTP / IMAP (email istihbaratı)

### 6.2 Karanlık Ağ & Anonimlik Ağları
- **Tor Network** (.onion adresleri, SOCKS5 proxy üzerinden)
- **I2P** (Invisible Internet Project — eepsite'lar)
- **Freenet** (FProxy üzerinden eski Freenet; Locutus/Hyphanet yeni nesil)
- **ZeroNet** (Bitcoin & BitTorrent tabanlı)
- **Retroshare** (şifreli P2P mesajlaşma ve paylaşım)
- **Hyphanet** (Freenet'in modern devamı)
- **Lokinet** (LLARP protokolü — Oxen ağı)

### 6.3 P2P Ağları
- **BitTorrent** (DHT, magnet linkleri, meta veri analizi)
- **IPFS** (InterPlanetary File System)
- **Gnutella / G2** (LimeWire mirasçısı ağlar)
- **eDonkey / eMule** (ed2k ağı)
- **Kad** (Kademlia DHT ağı)
- **Peers / WebRTC** (tarayıcı P2P)

### 6.4 Şifreli Mesajlaşma & Sosyal
- **Matrix** (Element — açık federatif mesajlaşma)
- **XMPP / Jabber** (bot ve log okuma)
- **IRC** (Internet Relay Chat — kanal takibi)
- **Nostr** (merkezsiz sosyal protokol)
- **Fediverse** (Mastodon, Pleroma, Lemmy — ActivityPub)
- **Briar** (Bluetooth/WiFi/Tor P2P)
- **Session** (Signal tabanlı, telefonsuz)
- **Tox** (P2P şifreli mesajlaşma protokolü)

### 6.5 Ham Ağ & Protokol
- **DNS** (kayıt çekme, zone transfer, passive DNS)
- **WHOIS** (domain kayıt sorguları)
- **BGP** (yönlendirme tablosu analizi)
- **SSL/TLS Sertifikaları** (sertifika şeffaflık logları — crt.sh)
- **SNMP** (ağ cihazı bilgisi)
- **NetFlow / IPFIX** (trafik analizi)
- **Shodan / Censys / ZoomEye API** (internet taraması servisleri)
- **SMTP/IMAP** (e-posta başlık ve meta analizi)

### 6.6 Radyo & Fiziksel Katman
- **SDR** (Software Defined Radio — RTL-SDR ile OSINT)
- **ADS-B** (uçak takibi — dump1090)
- **AIS** (gemi takibi)
- **APRS** (amatör radyo konum takibi)
- **Bluetooth LE tarama**
- **WiFi probe request analizi**

### 6.7 Blockchain & Kripto
- **Bitcoin** (adres, işlem, blok analizi)
- **Ethereum** (EVM zinciri; akıllı sözleşme, token takibi)
- **Monero** (karanlık ağ için sınırlı analiz)
- **TRON, BNB Chain, Solana** (genel zincir explorer API)
- **Chainalysis / Crystal / Arkham benzeri** yerel analiz

### 6.8 Özel API Servisleri
- Shodan, Censys, ZoomEye, FOFA (internet tarama)
- VirusTotal, MalwareBazaar (tehdit istihbaratı)
- Have I Been Pwned (veri ihlali sorgulama)
- Hunter.io, Clearbit (email/domain OSINT)
- ipinfo.io, AbuseIPDB (IP istihbaratı)
- Whoisfreaks, SecurityTrails (DNS/WHOIS geçmişi)
- Pastebin, Ghostbin, Rentry (paste takibi)

---

## 7. Kaynak Yönetim Sistemi

### 7.1 Kaynak Veri Yapısı

```sql
sources (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT,
  network_type ENUM('www','tor','i2p','p2p','freenet','zeronet','irc',
                    'matrix','rss','api','blockchain','sdr','custom'),
  plugin_id TEXT NOT NULL,
  auth_config JSONB,        -- Kimlik bilgileri (şifreli)
  proxy_config JSONB,       -- Proxy/VPN ayarları
  schedule TEXT,            -- Cron ifadesi
  priority INTEGER DEFAULT 5,
  enabled BOOLEAN DEFAULT TRUE,
  tags TEXT[],
  last_crawled_at TIMESTAMPTZ,
  last_success_at TIMESTAMPTZ,
  failure_count INTEGER DEFAULT 0,
  avg_response_ms INTEGER,
  metadata JSONB,           -- Plugin'e özel ek ayarlar
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
)
```

### 7.2 Kaynak Ekleme Akışı
1. Kullanıcı arayüzde kaynak tipini seçer (ağ türü + plugin)
2. Plugin'e özel form render edilir (dinamik şema tabanlı)
3. Bağlantı testi yapılır (opsiyonel)
4. Kaynak veritabanına kaydedilir
5. Collector Manager ilk çekimi tetikler
6. Sağlık durumu dashboard'da izlenir

---

## 8. Veri Akışı

```
[Kaynak]
    │
    ▼
[Collector Plugin]
    │  Ham veri (HTML, JSON, binary, vs.)
    ▼
[Message Queue (Redis/RabbitMQ)]
    │
    ▼
[Processing Pipeline]
    ├─ Temizleme & Normalizasyon
    ├─ Dil Tespiti
    ├─ Varlık Çıkarma (NER)
    ├─ Sınıflandırma
    ├─ Embedding Üretimi
    └─ İlişkilendirme
    │
    ▼
[PostgreSQL Veritabanı]
    │
    ├─ Query Engine ──────► Kullanıcı Arayüzü
    ├─ Graph Engine ──────► İlişki Görselleştirme
    ├─ Alert Manager ────► Bildirimler
    └─ Report Generator ► Raporlar / Dışa Aktarım
```

---

## 9. Veritabanı Tasarımı

### Ana Tablolar

```sql
-- Toplanan veri birimleri
items (
  id UUID PRIMARY KEY,
  source_id UUID REFERENCES sources(id),
  raw_content TEXT,
  cleaned_content TEXT,
  url TEXT,
  title TEXT,
  language CHAR(5),
  collected_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  content_hash CHAR(64) UNIQUE,  -- Yineleme önleme
  embedding VECTOR(1536),         -- pgvector
  metadata JSONB,
  tags TEXT[]
)

-- Çıkarılan varlıklar
entities (
  id UUID PRIMARY KEY,
  type ENUM('person','org','location','ip','domain','email',
             'phone','crypto_address','hash','username','cve','custom'),
  value TEXT NOT NULL,
  normalized_value TEXT,
  confidence FLOAT,
  first_seen_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ,
  metadata JSONB
)

-- Varlık-Veri ilişkisi
item_entities (
  item_id UUID REFERENCES items(id),
  entity_id UUID REFERENCES entities(id),
  mention_count INTEGER,
  context TEXT,
  PRIMARY KEY (item_id, entity_id)
)

-- Varlıklar arası ilişkiler (graf kenarları)
entity_relations (
  id UUID PRIMARY KEY,
  source_entity_id UUID REFERENCES entities(id),
  target_entity_id UUID REFERENCES entities(id),
  relation_type TEXT,
  weight FLOAT,
  evidence_count INTEGER,
  first_seen_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ
)

-- Kayıtlı sorgular & uyarılar
saved_queries (
  id UUID PRIMARY KEY,
  name TEXT,
  query_text TEXT,
  query_type ENUM('fts','semantic','regex','entity','graph'),
  alert_enabled BOOLEAN DEFAULT FALSE,
  alert_channels JSONB,
  last_triggered_at TIMESTAMPTZ
)
```

---

## 10. Güvenlik ve Gizlilik

### 10.1 Operasyonel Güvenlik (OPSEC)
- Tüm dış bağlantılar yapılandırılabilir proxy zincirine yönlendirilebilir (Tor → VPN → Hedef)
- Her kaynak için ayrı proxy/kimlik profili atanabilir
- Bağlantı parmak izi azaltma (User-Agent rotasyonu, TLS parmak izi maskeleme)
- DNS sızıntısı önleme (DNS-over-HTTPS / DNS-over-Tor)

### 10.2 Veri Güvenliği
- Veritabanı tam disk şifreleme (LUKS)
- Kimlik bilgileri Hashicorp Vault'ta saklanır (plain text yok)
- API anahtarları ve parolalar AES-256-GCM ile şifrelenir
- Raporlar GPG ile imzalanabilir ve şifrelenebilir

### 10.3 Erişim Kontrolü
- Çok kullanıcılı destek (RBAC — Role-Based Access Control)
- JWT tabanlı API kimlik doğrulama
- 2FA (TOTP — Google Authenticator uyumlu)
- Oturum zaman aşımı ve IP beyaz listesi

### 10.4 Denetim & Log
- Tüm API çağrıları loglanır (zaman damgası, kullanıcı, işlem)
- Değişmez log zinciri (append-only, hash zincirli)
- Log rotasyonu ve şifreli arşivleme

---

## 11. Self-Host Altyapı Gereksinimleri

### 11.1 Minimum Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---------|---------|---------|
| **CPU** | 4 çekirdek | 8-16 çekirdek |
| **RAM** | 8 GB | 32-64 GB |
| **Depolama** | 100 GB SSD | 1 TB+ NVMe |
| **Bant Genişliği** | 100 Mbps | 1 Gbps |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

### 11.2 VDS Servis Haritası (Docker Compose)

```yaml
servisler:
  osiris-core:       # Ana motor (C++)
  osiris-collector:  # Koleksiyon yöneticisi (Python)
  osiris-pipeline:   # İşleme hattı (Python)
  osiris-api:        # REST API sunucu
  
  postgresql:        # Ana veritabanı (port 5432)
  redis:             # Önbellek + kuyruk (port 6379)
  minio:             # Nesne depolama (port 9000)
  
  n8n:               # Otomasyon (port 5678)
  freshrss:          # RSS motoru (port 8080)
  
  nginx:             # Ters proxy + SSL
  vault:             # Sır yönetimi
```

### 11.3 Ağ Topolojisi

```
İnternet
   │
[Nginx / Caddy] (443/80)
   │
   ├── /api/*      → osiris-api
   ├── /n8n/*      → n8n
   ├── /rss/*      → freshrss
   └── /ui/*       → osiris-web-ui

[Internal Docker Network]
   osiris-core ←→ postgresql
   osiris-core ←→ redis
   osiris-collector ←→ redis (queue)
   osiris-pipeline ←→ redis (queue)
   osiris-pipeline ←→ postgresql
```

---

## 12. Plugin Mimarisi

### 12.1 Plugin Yapısı

```
plugins/
└── web-scraper/
    ├── manifest.json     # Plugin meta verisi ve şeması
    ├── collector.py      # Ana koleksiyon mantığı
    ├── requirements.txt  # Python bağımlılıkları
    └── README.md
```

### 12.2 manifest.json Örneği

```json
{
  "id": "web-scraper",
  "name": "Web Scraper",
  "version": "1.0.0",
  "network_type": "www",
  "author": "OSIRIS Team",
  "description": "Genel amaçlı web scraper",
  "config_schema": {
    "url": {"type": "string", "required": true},
    "depth": {"type": "integer", "default": 1},
    "follow_links": {"type": "boolean", "default": false},
    "css_selector": {"type": "string"}
  },
  "capabilities": ["html", "text", "links", "images"],
  "requires_proxy": false,
  "schedule_default": "0 */6 * * *"
}
```

### 12.3 Plugin Geliştirme Arayüzü (Python)

```python
from osiris.plugin import BaseCollector, CollectionResult

class MyCollector(BaseCollector):
    def collect(self, config: dict) -> CollectionResult:
        # Veri toplama mantığı buraya
        ...
        return CollectionResult(
            items=[...],
            metadata={...}
        )
    
    def health_check(self) -> bool:
        # Kaynak erişilebilirlik testi
        ...
```

---

## 13. Arayüz Katmanları

### 13.1 Qt6 Masaüstü İstemcisi
- **Hedef:** Ana güç kullanıcı arayüzü
- **Özellikler:** Tam özellikli, yerel performans, sistem tepsisi entegrasyonu
- **Bileşenler:**
  - Kaynak yönetim paneli
  - Gerçek zamanlı koleksiyon monitörü
  - Graf görselleştirici (Qt + QGraphicsView)
  - Gelişmiş sorgu oluşturucu
  - Uyarı yönetim merkezi
  - Rapor editörü

### 13.2 Tauri (Web Teknolojileri + Rust Backend)
- **Hedef:** Hafif, cross-platform alternatif
- **Avantaj:** Electron'a göre ~10x daha az bellek kullanımı
- **Frontend:** React veya Vue
- **Kullanım:** Uzak sunucuya bağlanan hafif istemci

### 13.3 Electron (Node.js + Web)
- **Hedef:** En geniş platform uyumluluğu
- **Frontend:** React
- **Kullanım:** Tauri'nin yerleşemediği ortamlar için

### 13.4 Web Arayüzü (Tarayıcı tabanlı)
- **Hedef:** Uzaktan erişim (VDS'e tarayıcıdan bağlanma)
- **Stack:** React + TypeScript + Tailwind
- **Özellik:** Mobil dahil tüm cihazlardan erişim

---

## 14. Otomasyon ve İş Akışları

### 14.1 N8N Entegrasyonu
N8N, OSIRIS'in otomasyon katmanıdır. OSIRIS API'ına özel N8N node'ları geliştirilerek şu iş akışları kurulabilir:

- **Tetikleyici:** Yeni varlık tespit edildiğinde → Telegram bildirimi gönder
- **Tetikleyici:** Belirli anahtar kelime bulunduğunda → Rapor oluştur ve email gönder
- **Zamanlanmış:** Her gece saat 03:00 → Günlük özet raporu üret
- **Zincirleme:** Yeni domain bulundu → WHOIS sorgula → Shodan tara → İlişki grafına ekle

### 14.2 FreshRSS Entegrasyonu
- FreshRSS, standart RSS/Atom kaynaklarını yönetir
- OSIRIS, FreshRSS'in veritabanını okuyarak yeni makaleleri kendi pipeline'ına alır
- FreshRSS arayüzü aynı zamanda ham feed okuyucu olarak kullanılır

### 14.3 Webhooks
- Dış sistemler OSIRIS'e push edebilir (örn: bir scraper servisi yeni veri bulduğunda)
- OSIRIS dış sistemlere push edebilir (uyarılar, raporlar)

---

## 15. Yol Haritası

### Faz 1 — Temel Altyapı (Ay 1-3)
- [ ] Core Engine (C++) — temel yapı, plugin sistemi, API sunucu
- [ ] PostgreSQL şema tasarımı ve kurulumu
- [ ] İlk 3 collector plugin: Web scraper, RSS, REST API
- [ ] Temel processing pipeline (temizleme, NER)
- [ ] Docker Compose altyapısı
- [ ] CLI arayüzü

### Faz 2 — Ağ Genişlemesi (Ay 4-6)
- [ ] Tor collector plugin
- [ ] I2P collector plugin
- [ ] IRC & Matrix collector plugin
- [ ] Shodan / Censys API entegrasyonu
- [ ] DNS / WHOIS modülleri
- [ ] Web UI (React) — temel ekranlar

### Faz 3 — Analiz Katmanı (Ay 7-9)
- [ ] Graf motoru (NetworkX)
- [ ] Semantik arama (pgvector + embedding)
- [ ] Uyarı yönetim sistemi
- [ ] Rapor üretici
- [ ] Qt6 masaüstü istemcisi (beta)

### Faz 4 — Otomasyon & Olgunlaşma (Ay 10-12)
- [ ] N8N entegrasyonu ve özel node'lar
- [ ] Blockchain analiz modülü
- [ ] SDR modülü (opsiyonel)
- [ ] Tauri istemcisi
- [ ] Tam dokümantasyon
- [ ] Test kapsamı (%80+)

---

## Ekler

### Referans Projeler & İlham Kaynakları

| Proje | İlgili Modül |
|-------|-------------|
| [Maltego](https://www.maltego.com) | Graf görselleştirme konsepti |
| [Spiderfoot](https://github.com/smicallef/spiderfoot) | OSINT otomasyon yaklaşımı |
| [Recon-ng](https://github.com/lanmaster53/recon-ng) | Plugin mimarisi |
| [TheHarvester](https://github.com/laramies/theHarvester) | Pasif keşif teknikleri |
| [OSINT Framework](https://osintframework.com) | Kaynak kategorileri |
| [OnionScan](https://github.com/s-rah/onionscan) | Tor ağı analizi |

### Lisans
OSIRIS — GNU General Public License v3.0 veya özel lisans (TBD)

---

*Bu doküman OSIRIS projesinin mimari ve planlama belgesidir. Geliştirme sürecinde güncellenecektir.*
*Oluşturulma: Ağustos 2026*
