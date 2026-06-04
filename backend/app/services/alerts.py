from dataclasses import dataclass
from typing import Protocol

from app.schemas.opportunity import OpportunityRead


@dataclass(frozen=True)
class AlertMessage:
    title: str
    body: str
    url: str | None = None


class AlertChannel(Protocol):
    async def send(self, message: AlertMessage) -> None:
        """Send an alert through Telegram, Discord, email, or another channel."""


def build_opportunity_alert(opportunity: OpportunityRead) -> AlertMessage:
    title = opportunity.nomenclature or f"SEACE opportunity {opportunity.seace_id}"
    body = "\n".join(
        part
        for part in [
            opportunity.entity_name,
            opportunity.process_type,
            opportunity.item_description,
        ]
        if part
    )
    return AlertMessage(title=title, body=body)
