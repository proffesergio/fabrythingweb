"""Shared helpers for the offline scrape scripts under tools/scrape/.

These scripts are never imported by Django -- they are run by hand under the
project venv to produce JSON fixtures that `seed_store_catalog` later loads.
Kept deliberately small and dependency-light (requests only).
"""
import json
import pathlib
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (fabrything catalog import; contact: bhnbids@gmail.com)"}


def polite_get(url, delay=1.0):
    """GET url with an identifying User-Agent, sleeping `delay` seconds first
    so we never exceed ~1 request/second against a partner's site. Raises on
    a non-200 response rather than silently scraping an error page."""
    time.sleep(delay)
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return r.text


def write_fixture(path, entries):
    """Write `entries` to `path` as a JSON fixture.

    Refuses to write an empty list: a run that collected zero products (a
    bad category path, a site-wide block, a transient network failure) must
    never silently overwrite a previously-good fixture with `[]`. Prints an
    error and leaves any existing file at `path` untouched instead. Returns
    True if the file was written, False if the write was refused -- callers
    should treat False as a fatal condition (non-zero exit)."""
    p = pathlib.Path(path)
    if not entries:
        print(f"ERROR: refusing to write {p} -- zero entries collected. "
              f"Leaving any existing fixture at that path untouched.")
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(entries)} entries -> {p}")
    return True
