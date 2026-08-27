"""OSIRIS Collector Manager.

Tüm veri toplama plugin'lerini yönetir: yükleme, paralel görev,
yeniden deneme, hız sınırlama ve ham veriyi kuyruğa iletme.
Bkz. doküman §5.2.
"""

from osiris_collector.manager import CollectorManager

__all__ = ["CollectorManager"]
__version__ = "0.1.0"
