from typing import Dict, List, Optional
from .models import FeatureMetadata

class FeatureRegistry:
    def __init__(self):
        self._registry: Dict[str, FeatureMetadata] = {}

    def register(self, metadata: FeatureMetadata) -> None:
        if metadata.name in self._registry:
            raise ValueError(f"Feature {metadata.name} already registered")
        self._registry[metadata.name] = metadata

    def get_metadata(self, name: str) -> Optional[FeatureMetadata]:
        return self._registry.get(name)

    def list_all(self) -> List[FeatureMetadata]:
        return list(self._registry.values())

    def get_by_category(self, category: str) -> List[FeatureMetadata]:
        return [meta for meta in self._registry.values() if meta.category == category]

registry = FeatureRegistry()
