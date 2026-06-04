import httpx
import pytest

from app.clients.seace import SeaceClient
from app.core.config import Settings


def make_settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
        SEACE_BASE_URL="https://seace.test",
        CRAWLER_INTERVAL=3600,
        SEACE_MAX_RETRIES=1,
    )


@pytest.mark.asyncio
async def test_search_opportunities_normalizes_response() -> None:
    payload = [
        {
            "idProcedimiento": 1211512,
            "detEntidad": " DIRECCION DE REDES INTEGRADAS DE SALUD LIMA ESTE ",
            "detTipoProceso": "Concurso Público de Servicios",
            "nomenclatura": "CP SER-SM-1-2026-DIRIS LE-1",
            "detObjeto": "Servicio",
            "fechaConvocatoria": "04/05/2026 16:55:00",
            "fechaFin": "02/06/2026 23:59:00",
            "detItem": "CONTRATACIÓN DEL SERVICIO...",
            "codCubso": "8116180100232695",
            "detCubso": "SERVICIO DE ALQUILER...",
            "sintesisProceso": "...",
            "estadoItem": "7",
        }
    ]

    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SeaceClient(make_settings(), http_client=http_client)
        result = await client.search_opportunities(keyword="software")

    assert len(result) == 1
    assert result[0].seace_id == 1211512
    assert result[0].keyword == "software"
    assert result[0].entity_name == "DIRECCION DE REDES INTEGRADAS DE SALUD LIMA ESTE"
    assert result[0].publish_date is not None
    assert seen_urls == [
        "https://seace.test/api/oportunidades/codObjeto/codDepartamento/"
        "sintesisProceso/codTipoProceso/0/0/software/0"
    ]


def test_normalize_response_skips_items_without_valid_id() -> None:
    client = SeaceClient(make_settings())

    result = client.normalize_response([{"idProcedimiento": None}, {"idProcedimiento": "42"}], keyword="cloud")

    assert len(result) == 1
    assert result[0].seace_id == 42
