#!/usr/bin/env python3
"""
Test OCR engines: claude | paddle | lighton
Usage:
    python test_engines.py <path_to_image_or_pdf> [engine]
    python test_engines.py doc.pdf          # testuje wszystkie 3
    python test_engines.py doc.pdf paddle   # tylko paddle
"""
import sys
import os
import time

def test_engine(engine: str, data: bytes, content_type: str):
    os.environ["OCR_ENGINE"] = engine
    # reload processor with new env
    import importlib
    import api.ocr.processor as proc
    importlib.reload(proc)
    proc.load_models()

    print(f"\n{'='*60}")
    print(f"ENGINE: {engine.upper()}")
    print('='*60)
    t0 = time.time()
    try:
        result = proc.run_ocr_on_bytes(data, content_type)
        elapsed = time.time() - t0
        print(f"Czas: {elapsed:.2f}s")
        print(f"Długość tekstu: {len(result)} znaków")
        print(f"\n--- WYNIK (pierwsze 800 znaków) ---")
        print(result[:800])
        if len(result) > 800:
            print(f"\n[... i jeszcze {len(result)-800} znaków]")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"BŁĄD po {elapsed:.2f}s: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_engines.py <file> [engine]")
        sys.exit(1)

    filepath = sys.argv[1]
    engine_arg = sys.argv[2] if len(sys.argv) > 2 else "all"

    with open(filepath, "rb") as f:
        data = f.read()

    content_type = "application/pdf" if filepath.endswith(".pdf") else "image/jpeg"

    # Add api dir to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    engines = ["claude", "paddle", "lighton"] if engine_arg == "all" else [engine_arg]
    for engine in engines:
        test_engine(engine, data, content_type)

    print(f"\n{'='*60}")
    print("KONIEC TESTÓW")

if __name__ == "__main__":
    main()
