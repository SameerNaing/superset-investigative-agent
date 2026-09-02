from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from ..schemas import StoredQueryResult


class QueryResultStoreService:
    def __init__(self, ttl_minutes: int = 30):
        self._memory: dict[str, StoredQueryResult] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = Lock()

    def save(
        self,
        execution_id: str,
        data: list[dict[str, Any]]
    ) -> str:
        now = datetime.now(timezone.utc)

        result = StoredQueryResult(
            execution_id=execution_id,
            data=data,
            created_at=now,
            expires_at=now + self._ttl,
        )

        with self._lock:
            self._cleanup_expired()
            self._memory[execution_id] = result

        return

    def get(self, execution_id: str) -> StoredQueryResult:
        with self._lock:
            result = self._memory.get(execution_id)

            if result is None:
                raise KeyError(
                    f"SQL execution result '{execution_id}' was not found."
                )

            if result.expires_at <= datetime.now(timezone.utc):
                del self._memory[execution_id]
                raise KeyError(
                    f"SQL execution result '{execution_id}' has expired."
                )

            return result

    def delete(self, execution_id: str) -> None:
        with self._lock:
            self._memory.pop(execution_id, None)

    def _cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)

        expired_ids = [
            execution_id
            for execution_id, result in self._memory.items()
            if result.expires_at <= now
        ]

        for execution_id in expired_ids:
            del self._memory[execution_id]