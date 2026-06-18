from pydantic import BaseModel

from app.schemas.dashboard import DashboardSummary
from app.schemas.invoice import InvoiceRead


class AssistantUploadResult(BaseModel):
    invoice: InvoiceRead
    summary_text: str
    needs_action: bool


class AssistantReviewSummary(BaseModel):
    invoices: list[InvoiceRead]
    summary_text: str
    count: int


class AssistantDashboardSummary(BaseModel):
    dashboard: DashboardSummary
    summary_text: str
    alerts: list[str]


class AssistantValidationResult(BaseModel):
    invoice: InvoiceRead
    summary_text: str
    success: bool


class AssistantHealthBrief(BaseModel):
    text: str
    risk_level: str
