from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.bank import (
    BankConnectionCompleteRequest,
    BankConnectionRead,
    BankConnectionStartResult,
    BankMatchingRunResult,
    BankSyncResult,
    BankTransactionCategoryUpdate,
    BankTransactionMatchRequest,
    BankTransactionRead,
    BankTransactionRuleRead,
    MatchSuggestion,
)
from app.services.bank_aggregator import BankAggregatorError
from app.services.bank_service import (
    BankAggregatorUnavailableError,
    BankConnectionNotFoundError,
    BankService,
    BankTransactionNotFoundError,
    BankTransactionRuleNotFoundError,
)
from app.services.invoice_transaction_matching_service import (
    InvoiceNotMatchableError,
    TransactionNotMatchableError,
)
from app.services.transaction_categorization_service import (
    DuplicateRulePatternError,
    EmptyRulePatternError,
    UnknownCategoryError,
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
    connection_id: str | None = None,
    service: BankService = Depends(get_bank_service),
) -> BankConnectionRead:
    return _complete_bank_callback(
        service,
        ref=ref,
        connection_id=connection_id,
    )


@router.post("/callback", response_model=BankConnectionRead)
def bank_callback_post(
    payload: BankConnectionCompleteRequest,
    service: BankService = Depends(get_bank_service),
) -> BankConnectionRead:
    return _complete_bank_callback(
        service,
        ref=payload.ref,
        connection_id=payload.connection_id,
        public_token=(
            payload.public_token
        ),
    )


def _complete_bank_callback(
    service: BankService,
    *,
    ref: str,
    connection_id: str | None = None,
    public_token: str | None = None,
) -> BankConnectionRead:
    try:
        return service.complete_connection(
            ref,
            upstream_connection_id=connection_id,
            public_token=(
                public_token
            ),
        )
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


@router.patch(
    "/transactions/{transaction_id}/category",
    response_model=BankTransactionRead,
)
def update_bank_transaction_category(
    transaction_id: UUID,
    payload: BankTransactionCategoryUpdate,
    service: BankService = Depends(get_bank_service),
) -> BankTransactionRead:
    try:
        return service.update_transaction_category(
            transaction_id,
            category_code=payload.category_code,
            create_rule=payload.create_rule,
            rule_pattern=payload.rule_pattern,
        )
    except BankTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_transaction_not_found"
        ) from exc
    except UnknownCategoryError as exc:
        raise HTTPException(status_code=400, detail="unknown_category") from exc
    except EmptyRulePatternError as exc:
        raise HTTPException(status_code=400, detail="empty_rule_pattern") from exc
    except DuplicateRulePatternError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate_rule_pattern",
        ) from exc


@router.post("/matching/run", response_model=BankMatchingRunResult)
def run_bank_transaction_matching(
    service: BankService = Depends(get_bank_service),
) -> BankMatchingRunResult:
    return BankMatchingRunResult(matched_count=service.run_transaction_matching())


@router.get(
    "/transactions/{transaction_id}/match-suggestions",
    response_model=list[MatchSuggestion],
)
def get_bank_transaction_match_suggestions(
    transaction_id: UUID,
    service: BankService = Depends(get_bank_service),
) -> list[MatchSuggestion]:
    try:
        return service.get_match_suggestions(transaction_id)
    except BankTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_transaction_not_found"
        ) from exc


@router.patch(
    "/transactions/{transaction_id}/match",
    response_model=BankTransactionRead,
)
def match_bank_transaction(
    transaction_id: UUID,
    payload: BankTransactionMatchRequest,
    service: BankService = Depends(get_bank_service),
) -> BankTransactionRead:
    try:
        return service.match_transaction(transaction_id, payload.invoice_id)
    except BankTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_transaction_not_found"
        ) from exc
    except TransactionNotMatchableError as exc:
        raise HTTPException(
            status_code=400, detail="transaction_not_matchable"
        ) from exc
    except InvoiceNotMatchableError as exc:
        raise HTTPException(
            status_code=400, detail="invoice_not_matchable"
        ) from exc


@router.delete(
    "/transactions/{transaction_id}/match",
    response_model=BankTransactionRead,
)
def unmatch_bank_transaction(
    transaction_id: UUID,
    service: BankService = Depends(get_bank_service),
) -> BankTransactionRead:
    try:
        return service.unmatch_transaction(transaction_id)
    except BankTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_transaction_not_found"
        ) from exc


@router.get("/transaction-rules", response_model=list[BankTransactionRuleRead])
def list_bank_transaction_rules(
    service: BankService = Depends(get_bank_service),
) -> list[BankTransactionRuleRead]:
    return service.list_transaction_rules()


@router.delete(
    "/transaction-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bank_transaction_rule(
    rule_id: UUID,
    service: BankService = Depends(get_bank_service),
) -> None:
    try:
        service.delete_transaction_rule(rule_id)
    except BankTransactionRuleNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="bank_transaction_rule_not_found"
        ) from exc
