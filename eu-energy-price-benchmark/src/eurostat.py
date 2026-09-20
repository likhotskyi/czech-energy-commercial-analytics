"""
A small Eurostat API client.

Eurostat serves JSON-stat 2.0, which is compact but not obvious: the `value`
object is a *sparse* map from a flat index to a number, and that index has to be
decoded against the dimension sizes in row-major (C) order. Missing observations
are simply absent from the map -- there are no nulls -- which is why this module
returns a tidy table with gaps rather than a dense matrix.

Everything is cached to disk. Re-running the analysis must not depend on the
network being up, and the cached JSON is what makes a result reproducible months
later when Eurostat has revised the series.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
USER_AGENT = "eu-energy-price-benchmark/1.0 (portfolio project; contact via GitHub)"


def build_url(dataset: str, params: dict[str, object]) -> str:
    """Eurostat repeats a parameter to select several values: &geo=CZ&geo=DE."""
    pairs: list[tuple[str, str]] = [("format", "JSON"), ("lang", "en")]
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            pairs.extend((key, str(v)) for v in value)
        else:
            pairs.append((key, str(value)))
    return f"{BASE}/{dataset}?{urllib.parse.urlencode(pairs)}"


def fetch(dataset: str, params: dict[str, object], cache_dir: Path,
          refresh: bool = False, retries: int = 3) -> dict:
    """Download a dataset, or read it back from the cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{dataset}.json"

    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    url = build_url(dataset, params)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:                       # network, timeout, bad gateway
            last_error = exc
            if attempt == retries - 1:
                raise RuntimeError(f"Eurostat request failed for {dataset}: {exc}") from exc
            time.sleep(2 * (attempt + 1))
    else:                                              # pragma: no cover
        raise RuntimeError(str(last_error))

    if "error" in payload:
        raise RuntimeError(f"Eurostat rejected the query for {dataset}: {payload['error']}")

    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def to_frame(payload: dict) -> pd.DataFrame:
    """
    Decode JSON-stat 2.0 into a tidy frame: one row per observation, one column
    per dimension, plus `value`. Dimension codes AND their human labels are kept,
    because a report that prints 'MWH2000-19999' at a reader is not a report.
    """
    dim_ids: list[str] = payload["id"]
    sizes: list[int] = payload["size"]

    # index position -> (code, label) for each dimension
    decoders: list[list[tuple[str, str]]] = []
    for dim_id in dim_ids:
        category = payload["dimension"][dim_id]["category"]
        index = category["index"]
        labels = category.get("label", {})
        if isinstance(index, dict):
            ordered = sorted(index.items(), key=lambda kv: kv[1])
            codes = [code for code, _ in ordered]
        else:                                          # already a list
            codes = list(index)
        decoders.append([(code, labels.get(code, code)) for code in codes])

    # Row-major strides: the last dimension varies fastest.
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    rows = []
    for flat_index, value in payload["value"].items():
        remainder = int(flat_index)
        row: dict[str, object] = {}
        for dim_id, stride, decoder in zip(dim_ids, strides, decoders):
            position, remainder = divmod(remainder, stride)
            code, label = decoder[position]
            row[dim_id] = code
            row[f"{dim_id}_label"] = label
        row["value"] = value
        rows.append(row)

    frame = pd.DataFrame(rows)
    frame.attrs["dataset_label"] = payload.get("label", "")
    frame.attrs["updated"] = payload.get("updated", "")
    return frame


def semester_to_date(period: str) -> pd.Timestamp:
    """'2025-S2' -> 2025-07-01, so semesters sort and plot correctly."""
    year, semester = period.split("-S")
    return pd.Timestamp(int(year), 1 if semester == "1" else 7, 1)
