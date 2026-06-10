import os
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

os.environ["SCHEDULER_ENABLED"] = "false"

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_identity, get_seace_client, get_session
from app.main import app
from app.schemas.opportunity import OpportunityCreate


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeSeaceClient:
    async def search_opportunities(
        self,
        *,
        keyword: str,
        cod_objeto: int = 0,
        cod_departamento: int = 0,
        cod_tipo_proceso: int = 0,
    ) -> list[OpportunityCreate]:
        return [
            OpportunityCreate(
                seace_id=1,
                entity_name="Entidad",
                process_type="Adjudicación Simplificada",
                nomenclature="AS-1-2026",
                object_type="Servicio",
                item_description="Software",
                cubso_code="123",
                cubso_description="Software",
                process_summary="Summary",
                publish_date=datetime(2026, 5, 4, 16, 55, tzinfo=ZoneInfo("America/Lima")),
                end_date=datetime(2026, 6, 2, 23, 59, tzinfo=ZoneInfo("America/Lima")),
                keyword=keyword,
                raw_json={"idProcedimiento": 1},
            )
        ]


class FakeRepository:
    async def bulk_insert_ignore_duplicates(self, opportunities: list[OpportunityCreate]) -> tuple[int, int]:
        return len(opportunities), 0


async def override_session():
    yield FakeSession()


def override_seace_client() -> FakeSeaceClient:
    return FakeSeaceClient()


def override_current_identity() -> SimpleNamespace:
    return SimpleNamespace(id=1, verification_status="verified", wallet_address="0x123")


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_crawl_endpoint(monkeypatch) -> None:
    from app.services import crawler as crawler_module

    monkeypatch.setattr(crawler_module, "OpportunityRepository", lambda session: FakeRepository())
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_seace_client] = override_seace_client
    app.dependency_overrides[get_current_identity] = override_current_identity

    try:
        with TestClient(app) as client:
            response = client.post("/crawl", json={"keyword": "software"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["inserted"] == 1
    assert response.json()["duplicates"] == 0


def test_protected_endpoint_requires_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.get("/opportunities")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"
