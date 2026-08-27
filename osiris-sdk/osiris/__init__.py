"""OSIRIS paylaşılan SDK'sı.

Plugin geliştirme arayüzü ve ortak veri modelleri.
Bkz. doküman §12.3.
"""

from osiris.plugin import BaseCollector, CollectionResult, CollectedItem
from osiris.models import Source, Entity, Item

__all__ = [
    "BaseCollector",
    "CollectionResult",
    "CollectedItem",
    "Source",
    "Entity",
    "Item",
]

__version__ = "0.1.0"
