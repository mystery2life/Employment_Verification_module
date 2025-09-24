"""
run_merge
---------
Tiny CLI to run the two adapters and build the unified JSON.

Usage:
    python run_merge.py <paystub_path> <ev_path>
    # you can pass one or both; missing files are treated as absent source
"""

from __future__ import annotations

import sys
import json
import traceback
from pathlib import Path
from time import perf_counter

# Adapters
from paystub_adaptor import (
    extract_paystub_structured,
    extract_read_text,
    extract_llm_fields,
)
from ev_adaptor import extract_ev_structured

# Merge
from merge.merge_engine import build_unified


def _checkpoint(label: str, t0: float | None = None) -> float:
    """
    Print a progress checkpoint and optionally the elapsed time since t0.
    Returns a fresh timestamp so you can chain checkpoints.
    """
    now = perf_counter()
    if t0 is None:
        print(f"[chk] {label}")
    else:
        print(f"[chk] {label}  (Δ {now - t0:.2f}s)")
    return now


def run(paystub_path: str | None, ev_path: str | None):
    print("=== merge pipeline start ===")
    t_all = perf_counter()

    paystub_raw = None
    ev_raw = None

    # ---------- PAYSTUB ----------
    if paystub_path and Path(paystub_path).exists():
        print(f"[paystub] input: {paystub_path}")
        t0 = _checkpoint("read paystub bytes")
        ps_bytes = Path(paystub_path).read_bytes()

        try:
            t0 = _checkpoint("DI structured extraction (prebuilt-payStub.us)", t0)
            ps_struct = extract_paystub_structured(ps_bytes)
            print(f"[paystub] structured keys: {len(ps_struct)}")
        except Exception:
            print("[paystub] ❌ structured extraction failed:")
            traceback.print_exc()
            ps_struct = {}

        try:
            t0 = _checkpoint("OCR read (prebuilt-read)", t0)
            raw_text = extract_read_text(ps_bytes)
            print(f"[paystub] OCR chars: {len(raw_text)}")
        except Exception:
            print("[paystub] ❌ OCR read failed:")
            traceback.print_exc()
            raw_text = ""

        try:
            t0 = _checkpoint("LLM extraction (hours/rate/title)", t0)
            llm = extract_llm_fields(raw_text) if raw_text else {}
            # flatten/normalize LLM into paystub schema
            if isinstance(llm, dict):
                for k, v in llm.items():
                    if isinstance(v, dict) and "value" in v:
                        ps_struct[k] = v
                    else:
                        ps_struct[k] = {"value": v, "confidence": 80.0}
            print(f"[paystub] after LLM keys: {len(ps_struct)}")
        except Exception:
            print("[paystub] ❌ LLM extraction failed:")
            traceback.print_exc()

        paystub_raw = ps_struct
        _ = _checkpoint("paystub done", t0)
    else:
        print("[paystub] (skipped) no file provided or path does not exist")

    # ---------- EMPLOYMENT VERIFICATION ----------
    if ev_path and Path(ev_path).exists():
        print(f"[ev] input: {ev_path}")
        t0 = _checkpoint("read EV bytes")
        ev_bytes = Path(ev_path).read_bytes()

        try:
            t0 = _checkpoint("DI custom model extraction", t0)
            ev_struct = extract_ev_structured(ev_bytes)
            print(f"[ev] structured keys: {len(ev_struct)}")
        except Exception:
            print("[ev] ❌ EV extraction failed:")
            traceback.print_exc()
            ev_struct = {}

        ev_raw = ev_struct
        _ = _checkpoint("ev done", t0)
    else:
        print("[ev] (skipped) no file provided or path does not exist")

    # ---------- MERGE ----------
    t0 = _checkpoint("merge build_unified")
    unified = build_unified(paystub_raw, ev_raw)
    _ = _checkpoint("merge done", t0)

    print("=== final unified JSON ===")
    print(json.dumps(unified, indent=2))

    print(f"=== pipeline finished in {perf_counter() - t_all:.2f}s ===")


if __name__ == "__main__":
    ps_arg = sys.argv[1] if len(sys.argv) > 1 else None
    ev_arg = sys.argv[2] if len(sys.argv) > 2 else None
    run(ps_arg, ev_arg)
