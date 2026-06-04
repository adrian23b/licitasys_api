import asyncio
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.opportunity import OpportunityCreate
from app.utils.datetime import clean_text, parse_seace_datetime


class SeaceClientError(RuntimeError):
    pass


class SeaceClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._external_client = http_client
        self.logger = get_logger(__name__)

    async def search_opportunities(
        self,
        *,
        keyword: str,
        cod_objeto: int = 0,
        cod_departamento: int = 0,
        cod_tipo_proceso: int = 0,
    ) -> list[OpportunityCreate]:
        raw_items = await self._fetch_raw(
            keyword=keyword,
            cod_objeto=cod_objeto,
            cod_departamento=cod_departamento,
            cod_tipo_proceso=cod_tipo_proceso,
        )
        return self.normalize_response(raw_items, keyword=keyword)

    def normalize_response(
        self,
        payload: Any,
        *,
        keyword: str,
    ) -> list[OpportunityCreate]:
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise SeaceClientError("SEACE response is not a JSON array")

        normalized: list[OpportunityCreate] = []
        for item in payload:
            if not isinstance(item, dict):
                self.logger.warning("seace_item_skipped_non_object", keyword=keyword)
                continue

            seace_id = item.get("idProcedimiento")
            try:
                seace_id_int = int(seace_id)
            except (TypeError, ValueError):
                self.logger.warning("seace_item_skipped_missing_id", keyword=keyword, raw=item)
                continue

            normalized.append(
                OpportunityCreate(
                    seace_id=seace_id_int,
                    entity_name=clean_text(item.get("detEntidad")),
                    process_type=clean_text(item.get("detTipoProceso")),
                    nomenclature=clean_text(item.get("nomenclatura")),
                    object_type=clean_text(item.get("detObjeto")),
                    item_description=clean_text(item.get("detItem")),
                    cubso_code=clean_text(item.get("codCubso")),
                    cubso_description=clean_text(item.get("detCubso")),
                    process_summary=clean_text(item.get("sintesisProceso")),
                    publish_date=parse_seace_datetime(item.get("fechaConvocatoria")),
                    end_date=parse_seace_datetime(item.get("fechaFin")),
                    keyword=keyword.strip().lower(),
                    raw_json=item,
                )
            )
        return normalized

    async def _fetch_raw(
        self,
        *,
        keyword: str,
        cod_objeto: int,
        cod_departamento: int,
        cod_tipo_proceso: int,
    ) -> Any:
        encoded_keyword = quote(keyword.strip())
        path = (
            "/api/oportunidades/codObjeto/codDepartamento/sintesisProceso/codTipoProceso/"
            f"{cod_objeto}/{cod_departamento}/{encoded_keyword}/{cod_tipo_proceso}"
        )
        base_url = str(self.settings.seace_base_url).rstrip("/")
        url = f"{base_url}{path}"
        timeout = httpx.Timeout(self.settings.seace_timeout_seconds)
        last_error: Exception | None = None

        for attempt in range(1, self.settings.seace_max_retries + 1):
            try:
                async with self._client(timeout=timeout) as client:
                    self.logger.info("seace_request_started", url=url, attempt=attempt, keyword=keyword)
                    response = await client.get(
                        url,
                        headers={
                            "Accept": "application/json, text/plain, */*",
                            "User-Agent": "seace-opportunities-backend/1.0",
                        },
                    )
                    response.raise_for_status()
                    self.logger.info("seace_request_finished", status_code=response.status_code, keyword=keyword)
                    return response.json()
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.TransportError, ValueError) as exc:
                last_error = exc
                self.logger.warning(
                    "seace_request_failed",
                    attempt=attempt,
                    max_retries=self.settings.seace_max_retries,
                    error=str(exc),
                    keyword=keyword,
                )
                if attempt < self.settings.seace_max_retries:
                    await asyncio.sleep(min(2**attempt, 10))

        raise SeaceClientError(f"SEACE request failed after retries: {last_error}") from last_error

    def _client(self, timeout: httpx.Timeout) -> httpx.AsyncClient:
        if self._external_client is not None:
            return _NoopAsyncClientContext(self._external_client)
        return httpx.AsyncClient(timeout=timeout, follow_redirects=True)


class _NoopAsyncClientContext:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self.client

    async def __aexit__(self, *args: object) -> None:
        return None
