from typing import Dict, Type, Any
_REGISTRY: Dict[str, Type] = {}

def register(name: str):
    def deco(cls):
        _REGISTRY[name] = cls
        return cls
    return deco

def create(name: str, **kwargs: Any):
    if name not in _REGISTRY:
        raise KeyError(f"Strategy '{name}' not found. Registered: {list(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)

def available() -> list[str]:
    return sorted(_REGISTRY)
