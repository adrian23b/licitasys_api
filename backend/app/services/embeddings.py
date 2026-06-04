from typing import Protocol

from app.schemas.opportunity import OpportunityRead


class EmbeddingProvider(Protocol):
    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for semantic search."""


class VectorStore(Protocol):
    async def upsert_opportunity(self, opportunity: OpportunityRead, vector: list[float]) -> None:
        """Persist a searchable vector representation of an opportunity."""


def opportunity_embedding_text(opportunity: OpportunityRead) -> str:
    parts = [
        opportunity.entity_name,
        opportunity.process_type,
        opportunity.nomenclature,
        opportunity.object_type,
        opportunity.item_description,
        opportunity.cubso_description,
        opportunity.process_summary,
    ]
    return "\n".join(part for part in parts if part)
