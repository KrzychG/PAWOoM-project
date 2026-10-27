import json
import logging

logger = logging.getLogger(__name__)

class JsonCache:
    def __init__(self, redis_client, prefix: str, ttl: int, resource_name: str = "bike"):
        self.client = redis_client
        self.prefix = prefix
        self.ttl = ttl
        self.resource_name = resource_name

    def _make_key(self, resource_id: str) -> str:
        return f"{self.prefix}:{self.resource_name}:{resource_id}"

    def get(self, resource_id: str):
        if self.client is None or getattr(self.client, 'down', False):
            return None, "BYPASS"
        try:
            key = self._make_key(resource_id)
            data = self.client.get(key)
            if data:
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                return json.loads(data), "HIT"
            return None, "MISS"
        except Exception as e:
            logger.error(f"Redis connection failure (get): {e}")
            return None, "BYPASS"

    def put(self, resource_id: str, payload: dict) -> bool:
        if self.client is None or getattr(self.client, 'down', False):
            return False
        try:
            key = self._make_key(resource_id)
            self.client.setex(key, self.ttl, json.dumps(payload))
            return True
        except Exception as e:
            logger.error(f"Redis connection failure (put): {e}")
            return False

    def delete(self, resource_id: str) -> bool:
        if self.client is None or getattr(self.client, 'down', False):
            return False
        try:
            key = self._make_key(resource_id)
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis connection failure (delete): {e}")
            return False

class MemoryRedis:
    def __init__(self):
        self.storage = {}
        self.down = False

    def get(self, key: str):
        if self.down:
            raise RuntimeError("Redis connection timeout")
        return self.storage.get(key)

    def setex(self, key: str, ttl: int, value: str):
        if self.down:
            raise RuntimeError("Redis connection timeout")
        self.storage[key] = value

    def delete(self, key: str):
        if self.down:
            raise RuntimeError("Redis connection timeout")
        if key in self.storage:
            del self.storage[key]

    def ping(self):
        if self.down:
            raise RuntimeError("Redis down")
        return True

    def close(self):
        pass