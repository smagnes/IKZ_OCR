import time
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
import csv
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import httpx
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from schemas import ScanResponse, ConfidenceScores, ScanStatsResponse, ApiKeyCreate, ApiKeyResponse
from ocr.processor import load_models, run_ocr_on_bytes
from ocr.classifier import classify, DOC_TYPE_LABELS
from ocr.parser import parse_document
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def send_webhook(url: str, payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload, headers={"X-IKZOCR-Event": "scan.completed"})
        logger.info("Webhook wysłany do %s", url)
    except Exception as exc:
        logger.warning("Webhook nieudany (%s): %s", url, exc)


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class Settings(BaseSettings):
    database_url: str = "postgresql://medyk:medyk@postgres:5432/medykocr"
    redis_url: str = "redis://redis:6379"
    nats_url: str = "nats://nats:4222"
    cors_origins: str = "http://localhost:3000,https://panel.ikzocr.pl"
    preload_models: bool = True
    jwt_secret: str = "ikzocr_jwt_secret_change_in_production_2026"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    email_from: str = "noreply@ikzocr.pl"

    class Config:
        env_file = ".env"


settings = Settings()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf", "image/tiff"}
MAX_SIZE_MB = 20
JWT_ALGO = "HS256"
JWT_EXPIRE = timedelta(days=7)


def create_token(user_id: str, email: str, name: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "name": name,
        "exp": datetime.now(timezone.utc) + JWT_EXPIRE,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGO)


async def verify_jwt_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brakuje tokenu Bearer")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGO])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy lub wygasły token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool(settings.database_url)
    await db.ensure_schema()
    await db.seed_demo_keys()
    if settings.preload_models:
        load_models()
    yield
    await db.close_pool()


app = FastAPI(
    title="IKZOCR API",
    version="1.0.0",
    description="OCR dla dokumentów medycznych — pierwsze w Polsce rozwiązanie AI dla branży medycznej",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Brakuje tokenu Bearer")
    raw = authorization.removeprefix("Bearer ").strip()
    record = await db.get_api_key_record(raw)
    if not record:
        raise HTTPException(status_code=403, detail="Nieprawidłowy klucz API")
    return record


async def verify_scan_quota(key_record: dict = Depends(verify_api_key)) -> dict:
    used = key_record["scans_this_month"]
    limit = key_record["scans_limit"]
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Przekroczono limit skanów dla planu {key_record['plan']} ({limit}/msc). Zmień plan na wyższy.",
        )
    return key_record


# ── AUTH ─────────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name: str
    email: str
    password: str
    facility_name: str = ""


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/auth/register", summary="Rejestracja konta")
async def register(body: RegisterBody):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Hasło musi mieć minimum 8 znaków")
    existing = await db.get_user_by_email(body.email.lower())
    if existing:
        raise HTTPException(status_code=409, detail="Konto z tym adresem email już istnieje")

    password_hash = _hash_pw(body.password)
    user = await db.create_user(body.name, body.email.lower(), password_hash)

    facility = body.facility_name or f"Placówka {body.name}"
    api_key_data = await db.create_user_api_key(
        name="Klucz główny",
        facility_name=facility,
        plan="starter",
        user_id=str(user["id"]),
    )

    token = create_token(str(user["id"]), user["email"], user["name"])
    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
        },
        "api_key": {
            "raw_key": api_key_data["raw_key"],
            "plan": "starter",
            "scans_limit": 200,
            "scans_this_month": 0,
        },
    }


@app.post("/auth/login", summary="Logowanie")
async def login(body: LoginBody):
    user = await db.get_user_by_email(body.email.lower())
    if not user or not _verify_pw(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Błędny email lub hasło")

    key_data = await db.get_user_api_key(str(user["id"]))
    plan = key_data["plan"] if key_data else "starter"
    scans_limit = key_data["scans_limit"] if key_data else 200
    scans_used = key_data["scans_this_month"] if key_data else 0

    token = create_token(str(user["id"]), user["email"], user["name"])
    return {
        "token": token,
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "plan": plan,
            "scans_limit": scans_limit,
            "scans_this_month": scans_used,
        },
    }


@app.get("/auth/me", summary="Dane zalogowanego użytkownika")
async def me(jwt_user: dict = Depends(verify_jwt_user)):
    user = await db.get_user_by_id(jwt_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    key_data = await db.get_user_api_key(str(user["id"]))
    return {
        "id": str(user["id"]),
        "name": user["name"],
        "email": user["email"],
        "plan": key_data["plan"] if key_data else "starter",
        "scans_limit": key_data["scans_limit"] if key_data else 200,
        "scans_this_month": key_data["scans_this_month"] if key_data else 0,
        "created_at": str(user["created_at"].date()),
    }


# ── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "service": "IKZOCR API"}


# ── OCR ──────────────────────────────────────────────────────────────────────

@app.post("/v1/scan", response_model=ScanResponse, summary="Skanuj dokument medyczny")
async def scan_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    key_record: dict = Depends(verify_scan_quota),
    x_ikz_silos_id: Optional[str] = Header(default=None),
    x_ikz_patient_id: Optional[str] = Header(default=None),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Nieobsługiwany format: {file.content_type}. Akceptowane: {', '.join(ALLOWED_TYPES)}",
        )

    data = await file.read()
    if len(data) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Plik zbyt duży (maks. {MAX_SIZE_MB} MB)")

    scan_id = str(uuid.uuid4())
    t_start = time.perf_counter()

    try:
        raw_text = run_ocr_on_bytes(data, file.content_type)
    except Exception as exc:
        logger.error("OCR error %s: %s", scan_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Błąd przetwarzania OCR")

    doc_type, type_confidence = classify(raw_text)
    fields, alerts, fields_conf = parse_document(raw_text, doc_type)

    patient = fields.pop("patient", None)
    pesel_masked = fields.pop("pesel_masked", None)
    doctor = fields.pop("doctor", None)
    facility = fields.pop("facility", None)
    exam_date = fields.pop("exam_date", None)

    text_conf = min(0.99, type_confidence + 0.02)
    units_conf = min(0.99, fields_conf - 0.04)
    overall = round((text_conf + fields_conf + units_conf) / 3, 2)

    elapsed_ms = int((time.perf_counter() - t_start) * 1000)
    logger.info("Skan %s | typ=%s | plan=%s | czas=%dms", scan_id, doc_type, key_record["plan"], elapsed_ms)

    ikz_examination_id = None
    if x_ikz_silos_id and doc_type.value != "inny":
        ikz_examination_id = abs(hash(scan_id)) % 100000

    source = "ikz_mobile" if x_ikz_silos_id else "api"

    await db.save_scan(
        scan_id=scan_id,
        api_key_id=str(key_record["id"]),
        doc_type=doc_type.value,
        doc_type_label=DOC_TYPE_LABELS[doc_type],
        patient=patient,
        pesel_masked=pesel_masked,
        doctor=doctor,
        facility=facility,
        exam_date=exam_date,
        fields=fields,
        alerts=alerts,
        raw_text=raw_text,
        confidence_overall=overall,
        processing_time_ms=elapsed_ms,
        ikz_silos_id=x_ikz_silos_id,
        ikz_examination_id=ikz_examination_id,
        source=source,
    )

    response = ScanResponse(
        scan_id=scan_id,
        status="ok",
        doc_type=doc_type,
        doc_type_label=DOC_TYPE_LABELS[doc_type],
        confidence=ConfidenceScores(text=text_conf, values=fields_conf, units=units_conf, overall=overall),
        patient=patient,
        pesel_masked=pesel_masked,
        doctor=doctor,
        facility=facility,
        exam_date=exam_date,
        fields=fields,
        alerts=alerts,
        raw_text=raw_text[:2000],
        processing_time_ms=elapsed_ms,
        ikz_examination_id=ikz_examination_id,
    )

    if key_record.get("webhook_url"):
        background_tasks.add_task(send_webhook, key_record["webhook_url"], response.model_dump(mode="json"))

    return response


@app.get("/v1/stats", response_model=ScanStatsResponse, summary="Statystyki skanowania")
async def get_stats(key_record: dict = Depends(verify_api_key)):
    data = await db.get_stats(str(key_record["id"]))
    return ScanStatsResponse(
        total_scans=data["total_scans"],
        scans_this_month=data["scans_this_month"],
        accuracy=data["accuracy"],
        avg_processing_ms=data["avg_processing_ms"],
        by_type=data["by_type"],
        by_source=data["by_source"],
        monthly_revenue=0.0,
    )


@app.get("/v1/documents", summary="Lista skanów")
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    doc_type: Optional[str] = Query(None),
    key_record: dict = Depends(verify_api_key),
):
    docs, total = await db.get_scans(str(key_record["id"]), page, limit, doc_type)
    return {"documents": docs, "total": total, "page": page, "limit": limit}


@app.get("/v1/documents/export", summary="Eksport skanów do CSV")
async def export_documents(key_record: dict = Depends(verify_api_key)):
    docs, _ = await db.get_scans(str(key_record["id"]), page=1, limit=10000)
    output = io.StringIO()
    fields = ["id", "doc_type", "doc_type_label", "patient", "pesel_masked",
              "exam_date", "doctor", "facility", "source", "confidence_overall",
              "processing_time_ms", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for doc in docs:
        row = {k: (str(doc[k]) if doc.get(k) is not None else "") for k in fields}
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ikzocr_export.csv"'},
    )


@app.get("/v1/documents/export.md", summary="Eksport skanów do Markdown")
async def export_documents_md(key_record: dict = Depends(verify_api_key)):
    docs, total = await db.get_scans(str(key_record["id"]), page=1, limit=10000)
    lines = [
        "# Eksport IKZOCR\n",
        f"Liczba dokumentów: **{total}**\n",
        "---\n",
    ]
    for doc in docs:
        conf = doc.get("confidence_overall")
        conf_str = f"{round(conf * 100)}%" if conf is not None else "—"
        fields_raw = doc.get("fields") or {}
        fields_md = ""
        if fields_raw:
            fields_md = "\n".join(f"  - **{k}:** {v}" for k, v in fields_raw.items())
        alerts_raw = doc.get("alerts") or []
        alerts_md = ", ".join(alerts_raw) if alerts_raw else "—"
        lines.append(
            f"## {doc.get('doc_type_label') or '—'}\n"
            f"- **ID:** `{doc['id']}`\n"
            f"- **Pacjent:** {doc.get('patient') or '—'}\n"
            f"- **PESEL:** {doc.get('pesel_masked') or '—'}\n"
            f"- **Placówka:** {doc.get('facility') or '—'}\n"
            f"- **Data badania:** {doc.get('exam_date') or '—'}\n"
            f"- **Pewność OCR:** {conf_str}\n"
            f"- **Alerty:** {alerts_md}\n"
            + (f"- **Pola:**\n{fields_md}\n" if fields_md else "")
            + f"- **Dodano:** {doc.get('created_at') or '—'}\n\n---\n"
        )
    content = "\n".join(lines)
    return StreamingResponse(
        iter([content]),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ikzocr_export.md"'},
    )


@app.get("/v1/documents/{scan_id}", summary="Szczegóły skanu")
async def get_document(scan_id: str, key_record: dict = Depends(verify_api_key)):
    doc = await db.get_scan_by_id(scan_id, str(key_record["id"]))
    if not doc:
        raise HTTPException(status_code=404, detail="Skan nie istnieje")
    return doc


def _doc_to_txt(doc: dict) -> str:
    fields = doc.get("fields") or {}
    alerts = doc.get("alerts") or []
    conf = doc.get("confidence_overall")
    lines = [
        "IKZOCR — wynik OCR",
        f"ID: {doc['id']}",
        "=" * 52,
        f"Typ dokumentu : {doc.get('doc_type_label') or '—'}",
        f"Pacjent       : {doc.get('patient') or '—'}",
        f"PESEL         : {doc.get('pesel_masked') or '—'}",
        f"Placówka      : {doc.get('facility') or '—'}",
        f"Data badania  : {doc.get('exam_date') or '—'}",
        f"Lekarz        : {doc.get('doctor') or '—'}",
        f"Pewność OCR   : {round(conf*100)+'%' if conf else '—'}",
        f"Alerty        : {', '.join(alerts) if alerts else '—'}",
        "", "WYNIKI / POLA:",
    ]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"  {k}:")
            for item in v:
                lines.append(f"    - {item}")
        else:
            lines.append(f"  {k}: {v}")
    lines += ["", "RAW TEXT (OCR):", "-" * 52, doc.get("raw_text") or ""]
    return "\n".join(lines)


def _doc_to_md(doc: dict) -> str:
    fields = doc.get("fields") or {}
    alerts = doc.get("alerts") or []
    conf = doc.get("confidence_overall")
    conf_str = f"{round(conf*100)}%" if conf else "—"
    md = [
        f"# {doc.get('doc_type_label') or 'Dokument OCR'}",
        f"> ID: `{doc['id']}`\n",
        "| Pole | Wartość |", "|------|---------|",
        f"| Pacjent | {doc.get('patient') or '—'} |",
        f"| PESEL | {doc.get('pesel_masked') or '—'} |",
        f"| Placówka | {doc.get('facility') or '—'} |",
        f"| Data badania | {doc.get('exam_date') or '—'} |",
        f"| Lekarz | {doc.get('doctor') or '—'} |",
        f"| Pewność OCR | {conf_str} |",
        f"| Alerty | {', '.join(alerts) if alerts else '—'} |",
        "", "## Wyniki",
    ]
    for k, v in fields.items():
        if isinstance(v, list):
            md.append(f"\n### {k.replace('_', ' ').capitalize()}")
            for item in v:
                md.append(f"- {item}")
        else:
            md.append(f"\n### {k.replace('_', ' ').capitalize()}")
            md.append(v)
    md += ["", "## Tekst surowy (OCR)", "```", doc.get("raw_text") or "", "```"]
    return "\n".join(md)


def _doc_to_csv(doc: dict) -> str:
    fields = doc.get("fields") or {}
    alerts = doc.get("alerts") or []
    conf = doc.get("confidence_overall")
    flat = {k: ("; ".join(v) if isinstance(v, list) else str(v)) for k, v in fields.items()}
    row = {
        "id": doc["id"], "doc_type": doc.get("doc_type_label") or "",
        "pacjent": doc.get("patient") or "", "pesel": doc.get("pesel_masked") or "",
        "placowka": doc.get("facility") or "", "data_badania": doc.get("exam_date") or "",
        "lekarz": doc.get("doctor") or "",
        "pewnosc_ocr": f"{round(conf*100)}%" if conf else "",
        "alerty": "; ".join(alerts), **flat,
    }
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(row.keys()))
    w.writeheader()
    w.writerow(row)
    return out.getvalue()


@app.get("/v1/documents/{scan_id}/export.txt", summary="Eksport skanu do TXT")
async def export_scan_txt(scan_id: str, key_record: dict = Depends(verify_api_key)):
    doc = await db.get_scan_by_id(scan_id, str(key_record["id"]))
    if not doc:
        raise HTTPException(status_code=404, detail="Skan nie istnieje")
    return StreamingResponse(
        iter([_doc_to_txt(doc)]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ikzocr_{scan_id[:8]}.txt"'},
    )


@app.get("/v1/documents/{scan_id}/export.md", summary="Eksport skanu do Markdown")
async def export_scan_md(scan_id: str, key_record: dict = Depends(verify_api_key)):
    doc = await db.get_scan_by_id(scan_id, str(key_record["id"]))
    if not doc:
        raise HTTPException(status_code=404, detail="Skan nie istnieje")
    return StreamingResponse(
        iter([_doc_to_md(doc)]),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ikzocr_{scan_id[:8]}.md"'},
    )


@app.get("/v1/documents/{scan_id}/export.csv", summary="Eksport skanu do CSV")
async def export_scan_csv(scan_id: str, key_record: dict = Depends(verify_api_key)):
    doc = await db.get_scan_by_id(scan_id, str(key_record["id"]))
    if not doc:
        raise HTTPException(status_code=404, detail="Skan nie istnieje")
    return StreamingResponse(
        iter([_doc_to_csv(doc)]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ikzocr_{scan_id[:8]}.csv"'},
    )


@app.delete("/v1/documents/{scan_id}", summary="Usuń skan")
async def delete_document(scan_id: str, key_record: dict = Depends(verify_api_key)):
    deleted = await db.delete_scan(scan_id, str(key_record["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Skan nie istnieje")
    return {"deleted": True, "scan_id": scan_id}


@app.post("/v1/api-keys", response_model=ApiKeyResponse, summary="Utwórz klucz API dla placówki")
async def create_api_key(body: ApiKeyCreate, key_record: dict = Depends(verify_api_key)):
    if key_record["plan"] not in ("pro", "enterprise", "demo"):
        raise HTTPException(status_code=403, detail="Tworzenie kluczy wymaga planu Pro lub wyższego")
    result = await db.create_api_key(body.name, body.facility_name, "starter")
    return ApiKeyResponse(
        key_id=str(result["id"]),
        name=result["name"],
        facility_name=result["facility_name"],
        key_prefix=result["key_prefix"],
        created_at=str(result["created_at"].date()),
        scans_this_month=0,
        plan=result["plan"],
        raw_key=result.get("raw_key"),
    )


class WebhookBody(BaseModel):
    webhook_url: Optional[str] = None


@app.patch("/v1/api-keys/{key_id}/webhook", summary="Ustaw URL webhooka dla klucza")
async def update_webhook(key_id: str, body: WebhookBody, key_record: dict = Depends(verify_api_key)):
    await db.set_webhook_url(key_id, body.webhook_url or None)
    return {"ok": True, "webhook_url": body.webhook_url}


class SendEmailBody(BaseModel):
    to: str
    scan_id: str


@app.post("/v1/documents/send-email", summary="Wyślij wynik skanu na email")
async def send_scan_email(body: SendEmailBody, key_record: dict = Depends(verify_api_key)):
    if not settings.smtp_host:
        raise HTTPException(status_code=503, detail="Email nie jest skonfigurowany. Dodaj SMTP_HOST do .env")
    doc = await db.get_scan_by_id(body.scan_id, str(key_record["id"]))
    if not doc:
        raise HTTPException(status_code=404, detail="Skan nie istnieje")

    html = f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;padding:20px">
    <h2 style="color:#0B1A30">Wynik OCR — IKZOCR</h2>
    <p><b>Typ dokumentu:</b> {doc.get('doc_type_label','—')}</p>
    <p><b>Pacjent:</b> {doc.get('patient','—')}</p>
    <p><b>Data badania:</b> {doc.get('exam_date','—')}</p>
    <p><b>Pewność:</b> {round((doc.get('confidence_overall') or 0)*100,1)}%</p>
    <hr/>
    <p style="color:#64748B;font-size:12px">Wygenerowano przez IKZOCR · ikzocr.pl</p>
    </body></html>
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Wynik OCR: {doc.get('doc_type_label','dokument')}"
    msg["From"] = settings.email_from
    msg["To"] = body.to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.email_from, body.to, msg.as_string())
    except Exception as exc:
        logger.error("Email error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Błąd wysyłki: {exc}")

    return {"ok": True, "sent_to": body.to}


@app.get("/v1/api-keys", summary="Lista kluczy API")
async def list_api_keys(key_record: dict = Depends(verify_api_key)):
    keys = await db.list_api_keys()
    return {"keys": [
        {
            "key_id": str(k["id"]),
            "name": k["name"],
            "facility_name": k["facility_name"],
            "key_prefix": k["key_prefix"],
            "plan": k["plan"],
            "scans_limit": k["scans_limit"],
            "scans_this_month": k["scans_this_month"],
            "is_active": k["is_active"],
            "created_at": str(k["created_at"].date()),
        }
        for k in keys
    ]}

@app.post("/translate", summary="Medical document translation")
async def translate_document(
    file: UploadFile = File(...),
    authorization: str = Header(...),
):
    try:
        token = authorization.split(" ", 1)[1]
        from jose import jwt as jose_jwt
        jose_jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    import anthropic as _anthropic, os, json as _json, base64 as _b64, time as _time, re as _re, io as _io
    data = await file.read()
    t_start = _time.perf_counter()
    client = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY",""))

    try:
        media = (file.content_type or "").lower()
        b64 = _b64.b64encode(data).decode()

        # Step 1: OCR - extract original text verbatim
        if "pdf" in media:
            ocr_msg = client.beta.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=4000,
                betas=["pdfs-2024-09-25"],
                messages=[{"role": "user", "content": [
                    {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                    {"type": "text", "text": "Extract ALL text from this medical document verbatim in the original language. Return only the raw text, nothing else."}
                ]}])
        else:
            if media not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
                media = "image/jpeg"
            ocr_msg = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=4000,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
                    {"type": "text", "text": "Extract ALL text from this medical document verbatim in the original language. Return only the raw text, nothing else."}
                ]}])

        original_text = ocr_msg.content[0].text.strip()

        # Step 2: Translate and structure
        trans_prompt = ('Analyze this medical document and respond ONLY with valid JSON (no markdown, no extra text):\n'
                        '{"source_language":"language name","translated_text":"full structured English translation",'
                        '"document_type":"e.g. Lab Results / Discharge Summary / ECG",'
                        '"key_findings":[{"label":"param","value":"val with units","flag":"normal|high|low"}],'
                        '"clinical_notes":"2-3 sentence summary for physician"}\n\nDOCUMENT:\n')
        trans_msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=3000,
            messages=[{"role": "user", "content": trans_prompt + original_text}])

        raw = trans_msg.content[0].text.strip()
        raw = _re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = _re.sub(r"\n?```$", "", raw).strip()
        if not raw:
            raise ValueError("Empty response from Claude")
        result = _json.loads(raw)
    except Exception as exc:
        logger.error("Translate error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}")

    result["original_text"] = original_text
    result["processing_time_ms"] = int((_time.perf_counter() - t_start) * 1000)
    result.setdefault("key_findings", [])
    result.setdefault("clinical_notes", "")
    return result
