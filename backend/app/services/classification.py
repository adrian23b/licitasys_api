from dataclasses import dataclass
from typing import Protocol

from app.schemas.opportunity import OpportunityRead


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    confidence: float
    labels: list[str]


class OpportunityClassifier(Protocol):
    async def classify(self, opportunity: OpportunityRead) -> ClassificationResult:
        """Classify an opportunity for downstream filtering or alerts."""


class NoopOpportunityClassifier:
    async def classify(self, opportunity: OpportunityRead) -> ClassificationResult:
        return ClassificationResult(category="unclassified", confidence=0.0, labels=[])
