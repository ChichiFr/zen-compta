from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.bank import (
    BankConnectionRead,
    BankConnectionStartResult,
    BankSyncResult,
    BankTransactionRead,
)
from app.services.bank_aggregator import BankAggregatorError
from app.services.bank_service import (
    BankAggregatorUnavailableError,
    BankConnectionNotFoundError,
    BankService,
)

router = APIRouter(prefix="/bank", tags=["bank"])


def get_bank_service(db: Session = Depends(get_db)) -> BankService:
    return BankService(db)


@router.post("/connect", response_model=BankConnectionStartResult)
def start_bank_connection(
    service: BankService = Depends(get_bank_service),
) -> BankConnectionStartResult:
    try:
        connection = service.start_connection()
    except BankAggregatorUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bank_aggregator_unavailable",
        ) from exc
    except BankAggregatorError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bank_aggregator_error",
        ) from exc

    return BankConnectionStartResult(
        connection=connection,
        auth_link=connection.auth_link,
    )


@router.get("/callback", response_model=BankConnectionRead)
def bank_callback(
    ref: str,
    service: BankService = Depends(get_bank_service),
) -> BankConnectionRead:
    try:
        return service.complete_connection(ref)
    except BankConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_connection_not_found"
        ) from exc
    except BankAggregatorUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bank_aggregator_unavailable",
        ) from exc
    except BankAggregatorError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bank_aggregator_error",
        ) from exc


@router.get("/connections", response_model=list[BankConnectionRead])
def list_bank_connections(
    service: BankService = Depends(get_bank_service),
) -> list[BankConnectionRead]:
    return service.list_connections()


@router.post("/connections/{connection_id}/sync", response_model=BankSyncResult)
def sync_bank_transactions(
    connection_id: UUID,
    service: BankService = Depends(get_bank_service),
) -> BankSyncResult:
    try:
        new_transactions_count = service.sync_transactions(connection_id)
        total_transactions_count = service.count_transactions(connection_id)
    except BankConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_connection_not_found"
        ) from exc
    except BankAggregatorUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bank_aggregator_unavailable",
        ) from exc
    except BankAggregatorError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bank_aggregator_error",
        ) from exc

    return BankSyncResult(
        connection_id=connection_id,
        new_transactions_count=new_transactions_count,
        total_transactions_count=total_transactions_count,
    )


@router.get(
    "/connections/{connection_id}/transactions",
    response_model=list[BankTransactionRead],
)
def list_bank_transactions(
    connection_id: UUID,
    service: BankService = Depends(get_bank_service),
) -> list[BankTransactionRead]:
    try:
        return service.list_transactions(connection_id)
    except BankConnectionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_connection_not_found"
        ) from exc
