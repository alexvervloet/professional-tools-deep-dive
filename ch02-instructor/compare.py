"""
Chapter 2 measurement: the three-way, on shape AND on meaning.

Runs hand-rolled vs Instructor vs provider-native over the five trap postings
(× REPS), on a cloud model and a local one. Two different questions get
measured, because they have different answers:

  1. SHAPE: did a validated JobPosting come back at all, and how many HTTP
     calls did it take? This is what the tools advertise.
  2. MEANING: did the *values* survive the traps (hourly rate NOT annualized,
     hybrid NOT remote, prose date to ISO, NOK spotted)? The schema transport
     can't save you here; this is where "structured output" ends and
     "correct extraction" begins. Checked with TRAPS below: the same checks
     for every approach, per this series' rule: hold the judge constant.

Run it (several minutes; the local model is the slow half):

    secrun python ch02-instructor/compare.py
"""

import os
import sys
import time
from datetime import date

from dotenv import load_dotenv

import hand_rolled
import with_tool
from extraction import POSTINGS, JobPosting

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Run via secrun so OPENAI_API_KEY is set (see ../docs/SECRETS.md).")

REPS = 2

# Per-posting semantic checks: (field-level expectations that the traps test).
TRAPS: dict[str, dict[str, object]] = {
    "baseline (the dive's own)": {
        "salary_min": 80000, "salary_max": 95000, "currency": "EUR", "remote": True,
    },
    "hourly-rate trap": {"salary_min": None, "salary_max": None, "currency": None},
    "hybrid + no-comp trap": {"remote": False, "salary_min": None},
    "prose-date + GBP trap": {"apply_by": date(2026, 8, 31), "currency": "GBP", "remote": False},
    "foreign-language trap": {
        "salary_min": 600000, "salary_max": 700000, "currency": "NOK",
        "apply_by": date(2026, 8, 15), "remote": False,
    },
}

APPROACHES = {
    "hand-rolled": hand_rolled.extract,
    "instructor": with_tool.instructor_extract,
    "native": with_tool.native_extract,
}


def trap_misses(name: str, job: JobPosting) -> list[str]:
    return [
        f"{field}={getattr(job, field)!r} (want {want!r})"
        for field, want in TRAPS[name].items()
        if getattr(job, field) != want
    ]


all_misses: dict[str, list[str]] = {label: [] for label in APPROACHES}

for backend in ("openai", "ollama"):
    print(f"\n════ {backend} "
          f"({hand_rolled.OPENAI_MODEL if backend == 'openai' else hand_rolled.OLLAMA_MODEL}, "
          f"temperature={hand_rolled.TEMPERATURE}) ════")
    print(f"  {'approach':12} {'ok':>5} {'1-call':>7} {'calls':>6} {'traps':>7} {'sec/req':>8}")
    for label, fn in APPROACHES.items():
        ok = first_try = calls_total = traps_passed = traps_total = 0
        runs = 0
        started = time.perf_counter()
        for name, posting in POSTINGS.items():
            for _ in range(REPS):
                runs += 1
                try:
                    job, calls = fn(backend, posting)
                except Exception as e:
                    calls_total += 1 + hand_rolled.MAX_RETRIES
                    print(f"    ! {label}/{name}: {type(e).__name__}: {str(e)[:90]}")
                    continue
                ok += 1
                first_try += calls == 1
                calls_total += calls
                misses = trap_misses(name, job)
                traps_total += len(TRAPS[name])
                traps_passed += len(TRAPS[name]) - len(misses)
                for miss in misses:
                    all_misses[label].append(f"{backend}/{name}: {miss}")
        elapsed = time.perf_counter() - started
        print(f"  {label:12} {ok:>3}/{runs:<2} {first_try:>5}/{runs:<2} {calls_total:>5} "
              f"{traps_passed:>4}/{traps_total:<3} {elapsed / runs:>7.1f}s")

print("\n── semantic misses by approach (the traps that got through)")
for label, misses in all_misses.items():
    print(f"  {label}: {len(misses)}")
    for miss in misses:
        print(f"    - {miss}")
