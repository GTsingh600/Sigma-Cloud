"""
In-process cache for deserialized model artifacts.

joblib.load on a boosted-tree pipeline is expensive enough to matter per
request, but an unbounded dict is a slow memory leak on a small instance - and
a stale entry keeps serving a model the user already deleted. Bounded LRU with
explicit invalidation on both counts.
"""
from __future__ import annotations

import logging
import os
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional

import joblib

logger = logging.getLogger(__name__)

MAX_CACHED_MODELS = 4

_cache: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
_lock = threading.Lock()


class ModelArtifactMissing(FileNotFoundError):
    """The serialized model is no longer on disk."""


def load(model_id: int, file_path: Optional[str]) -> Dict[str, Any]:
    if not file_path or not os.path.exists(file_path):
        invalidate(model_id)
        raise ModelArtifactMissing(file_path or "<unset>")

    with _lock:
        cached = _cache.get(model_id)
        if cached is not None:
            _cache.move_to_end(model_id)
            return cached

    # Deserialize outside the lock so a slow load does not block other requests.
    artifact = joblib.load(file_path)

    with _lock:
        _cache[model_id] = artifact
        _cache.move_to_end(model_id)
        while len(_cache) > MAX_CACHED_MODELS:
            evicted, _ = _cache.popitem(last=False)
            logger.debug("Evicted model %s from cache", evicted)

    logger.info("Model %s loaded into cache", model_id)
    return artifact


def invalidate(model_id: int) -> None:
    with _lock:
        _cache.pop(model_id, None)


def clear() -> None:
    with _lock:
        _cache.clear()
