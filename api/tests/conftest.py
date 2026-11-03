"""Testy API na prawdziwym Postgresie (TEST_DATABASE_URL), z zaślepionym silnikiem OCR."""
import os
import sys
import types
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

# Ciężkie silniki OCR (Paddle/torch/Claude) nie są potrzebne do testów izolacji
_proc = types.ModuleType("ocr.processor")
_proc.load_models = lambda: None
_proc.run_ocr_on_bytes = lambda data, ct: (
    "LABORATORIUM TESTOWE\nMorfologia krwi\nPacjent: Jan Testowy\nData: 2026-11-01\n"
    "WBC 6.5 10^3/ul 4.0-10.0\nHGB 14.1 g/dl 12.0-16.0\n"
)
sys.modules["ocr.processor"] = _proc
_ext = types.ModuleType("ocr.extractor")
_ext.extract_structured = lambda text: {}
sys.modules["ocr.extractor"] = _ext

os.environ.setdefault("PRELOAD_MODELS", "false")
DSN = os.environ.get("TEST_DATABASE_URL", "postgresql://medyk:medyk@localhost:55432/medykocr_test")

import db  # noqa: E402
import main  # noqa: E402


@pytest.fixture
async def client():
    import httpx

    await db.init_pool(DSN)
    pool = db.get_pool()
    await pool.execute("DROP TABLE IF EXISTS scans, api_keys, facilities, users CASCADE")
    await pool.execute((API_DIR.parent / "init.sql").read_text())
    await db.ensure_schema()
    await db.seed_demo_keys()
    for lim in (main.demo_session_limiter, main.demo_scan_limiter, main.demo_request_limiter):
        lim.reset()

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db.close_pool()
    db._pool = None
