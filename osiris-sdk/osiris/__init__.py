"""OSIRIS paylaşılan SDK'sı.

Plugin geliştirme arayüzü ve ortak veri modelleri.
Bkz. doküman §12.3.
"""

from osiris.models import Entity, Item, Source
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult

__all__ = [
    "BaseCollector",
    "CollectionResult",
    "CollectedItem",
    "Source",
    "Entity",
    "Item",
]

__version__ = "0.1.0"
