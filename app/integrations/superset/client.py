"""Superset HTTP client.

Reuses the authentication and endpoint patterns from the former
`superset_analytics_tools` package. Transformation belongs in the adapter.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import requests

from app.config import Settings, get_settings


class SupersetClientError(RuntimeError):
    pass


class SupersetClient:
    def __init__(
        self,
        settings: Settings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session or requests.Session()
        self._token: str | None = None

    @property
    def api_base(self) -> str:
        base = self._settings.superset_base_url
        if not base:
            raise SupersetClientError(
                "SUPERSET_BASEURL is not configured",
            )
        return f"{base}/api/v1/"

    def _url(self, path: str) -> str:
        return urljoin(self.api_base, path.lstrip("/"))

    def login(self, *, with_csrf: bool = False) -> str:
        payload = {
            "password": self._settings.superset_password,
            "provider": "db",
            "refresh": True,
            "username": self._settings.superset_username,
        }
        response = self._session.post(
            self._url("security/login"),
            json=payload,
            headers={"Accept": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        self._token = token
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )
        if with_csrf:
            csrf_res = self._session.get(
                self._url("security/csrf_token/"),
                headers={"Accept": "application/json"},
                timeout=30,
            )
            csrf_res.raise_for_status()
            self._session.headers["X-CSRFToken"] = csrf_res.json()["result"]
        return token

    def _ensure_auth(self) -> None:
        if not self._token:
            self.login()

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        self._ensure_auth()
        response = self._session.get(
            self._url(path),
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, *, json_body: dict[str, Any]) -> Any:
        self._ensure_auth()
        response = self._session.post(
            self._url(path),
            json=json_body,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def get_chart(self, chart_id: int) -> dict[str, Any]:
        """GET /api/v1/chart/{id} — includes params and query_context strings."""
        payload = self._get(f"chart/{chart_id}")
        result = payload.get("result") or {}
        if isinstance(result.get("params"), str):
            try:
                result["params"] = json.loads(result["params"])
            except json.JSONDecodeError:
                result["params"] = {}
        if isinstance(result.get("query_context"), str):
            try:
                result["query_context"] = json.loads(result["query_context"] or "{}")
            except json.JSONDecodeError:
                result["query_context"] = {}
        elif result.get("query_context") is None:
            result["query_context"] = {}
        return result

    def get_dataset(self, dataset_id: int) -> dict[str, Any]:
        """GET /api/v1/dataset/{id} — columns, saved metrics, time_grain_sqla.

        ``time_grain_sqla`` is ``[[duration, label], ...]`` for this dataset's
        database: builtin grains plus ``TIME_GRAIN_ADDONS``, minus denylist.
        There is no separate time-grain API.
        """
        payload = self._get(f"dataset/{dataset_id}")
        return payload.get("result") or {}

    def get_chart_list(
        self,
        *,
        page: int = 0,
        page_size: int = 100,
        datasource_id: int | None = None,
    ) -> list[dict[str, Any]]:
        q_parts = [f"page:{page}", f"page_size:{page_size}"]
        if datasource_id is not None:
            q_parts.append(
                f"filters:!((col:datasource_id,opr:eq,value:{datasource_id}))"
            )
        payload = self._get("chart/", params={"q": f"({','.join(q_parts)})"})
        return payload.get("result") or []

    def get_dataset_list(
        self,
        *,
        page: int = 0,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        q = f"(page:{page},page_size:{page_size})"
        payload = self._get("dataset/", params={"q": q})
        return payload.get("result") or []

    def get_chart_data(
        self,
        query_context: dict[str, Any],
        *,
        result_type: str = "results",
    ) -> list[dict[str, Any]]:
        body = {**query_context, "result_type": result_type}
        payload = self._post("chart/data", json_body=body)
        return payload.get("result") or []

    def execute_sql(
        self,
        database_id: int,
        sql: str,
        *,
        query_limit: int = 1000,
    ) -> dict[str, Any]:
        self.login(with_csrf=True)
        response = self._session.post(
            self._url("sqllab/execute/"),
            json={
                "database_id": database_id,
                "sql": sql,
                "queryLimit": query_limit,
            },
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
