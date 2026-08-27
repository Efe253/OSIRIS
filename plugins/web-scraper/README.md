# Web Scraper Plugin

Genel amaçlı web sayfası toplama plugin'i.

## Yapılandırma

| Alan | Tip | Zorunlu | Varsayılan | Açıklama |
|------|-----|---------|-----------|----------|
| `url` | string | evet | — | Hedef URL |
| `depth` | integer | hayır | 1 | Tarama derinliği |
| `follow_links` | boolean | hayır | false | Bağlantıları takip et |
| `css_selector` | string | hayır | — | Belirli bir CSS seçicisini çek |

## Kullanım

```python
from web_scraper.collector import WebScraperCollector

collector = WebScraperCollector({"url": "https://example.com"})
result = collector.collect()
print(result.items)
```
