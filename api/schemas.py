from pydantic import BaseModel
from typing import Optional
from enum import Enum


class DocType(str, Enum):
    morfologia = "morfologia"
    recepta = "recepta"
    skierowanie = "skierowanie"
    wynik_laboratoryjny = "wynik_laboratoryjny"
    ekg = "ekg"
    rtg_usg = "rtg_usg"
    epikryza = "epikryza"
    karta_informacyjna = "karta_informacyjna"
    inny = "inny"


class ScanAlert(str, Enum):
    anemia = "anemia"
    leukocytoza = "leukocytoza"
    hiperglikemia = "hiperglikemia"
    hipoglikemia = "hipoglikemia"
    nadcisnienie = "nadcisnienie"
    niedoczynnosc_tarczycy = "niedoczynnosc_tarczycy"
    nadczynnosc_tarczycy = "nadczynnosc_tarczycy"
    pilne = "pilne"


class ConfidenceScores(BaseModel):
    text: float
    values: float
    units: float
    overall: float


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    doc_type: DocType
    doc_type_label: str
    confidence: ConfidenceScores
    patient: Optional[str] = None
    pesel_masked: Optional[str] = None
    doctor: Optional[str] = None
    facility: Optional[str] = None
    exam_date: Optional[str] = None
    fields: dict
    alerts: list[str]
    raw_text: str
    processing_time_ms: int
    ikz_examination_id: Optional[int] = None


class ApiKeyCreate(BaseModel):
    name: str
    facility_name: str


class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    facility_name: str
    key_prefix: str
    created_at: str
    scans_this_month: int
    plan: str
    raw_key: Optional[str] = None


class ScanStatsResponse(BaseModel):
    total_scans: int
    scans_this_month: int
    accuracy: float
    avg_processing_ms: int
    by_type: dict
    by_source: dict
    monthly_revenue: float
