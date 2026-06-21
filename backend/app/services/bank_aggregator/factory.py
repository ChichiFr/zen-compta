from app.core.config import settings
from app.services.bank_aggregator.base import BankAggregator
from app.services.bank_aggregator.gocardless import GoCardlessAggregator


def build_bank_aggregator() -> BankAggregator | None:
    provider = settings.bank_aggregator_provider.lower()
    if provider == "gocardless":
        if not settings.gocardless_secret_id or not settings.gocardless_secret_key:
            return None
        return GoCardlessAggregator(
            secret_id=settings.gocardless_secret_id,
            secret_key=settings.gocardless_secret_key,
        )
    raise ValueError(f"unknown_bank_aggregator_provider: {provider}")
