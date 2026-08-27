# OSIRIS'e Katkı

OSIRIS'e katkıda bulunduğunuz için teşekkürler. Aşağıdaki kurallar, tutarlı ve sürdürülebilir bir kod tabanı sağlamak içindir.

## Geliştirme Ortamı

```bash
# Sanal ortam oluştur
python3 -m venv .venv
source .venv/bin/activate

# SDK ve modülleri kur
pip install -e ./osiris-sdk
pip install -e ./osiris-collector
pip install -e ./osiris-pipeline
pip install -e ./osiris-graph
pip install -e ./osiris-alert
pip install -e ./osiris-report
pip install -e ./osiris-query
pip install -e ./osiris-api
pip install -e ./osiris-cli

# Testleri çalıştır
pytest
```

## Yeni Plugin Ekleme

1. `plugins/<plugin-id>/` dizini oluştur.
2. `manifest.json` yaz (id, name, network_type, config_schema).
3. `collector.py` içinde `BaseCollector`'dan türeyen bir sınıf yaz.
4. `requirements.txt` ekle.
5. `osiris plugins` komutuyla yüklendiğini doğrula.

## Kod Standartları

- Python: `ruff` ile lint (bkz. `pyproject.toml`).
- C++: C++20, `-Wall -Wextra -Wpedantic`.
- Testler: `pytest`, her modülün `tests/` dizininde.
- Commit mesajları: `Faz N: kısa açıklama` formatı.

## Commit Kuralları

- Her mantıksal değişiklik ayrı bir commit olmalı.
- Önemli değişikliklerde faz bazlı commit atılır.
- Commit mesajı Türkçe, açıklayıcı ve kısa olmalı.
