from __future__ import annotations

from math import sqrt
from typing import Iterable

from .ingest import IngestRecord


def domain_correlation_matrix(
    records: Iterable[IngestRecord], *, condition: str
) -> dict[str, dict[str, float]]:
    """Estimate pairwise Pearson correlations from downstream domain observations."""
    rows = [r.state.domain_scores for r in records if r.condition == condition]
    domains = sorted(set().union(*(row.keys() for row in rows))) if rows else []
    matrix: dict[str, dict[str, float]] = {d: {} for d in domains}
    for a in domains:
        xa = [float(row.get(a, 0.0)) for row in rows]
        ma = sum(xa) / len(xa) if xa else 0.0
        da = sum((x - ma) ** 2 for x in xa)
        for b in domains:
            xb = [float(row.get(b, 0.0)) for row in rows]
            mb = sum(xb) / len(xb) if xb else 0.0
            db = sum((y - mb) ** 2 for y in xb)
            if a == b:
                corr = 1.0
            else:
                denom = sqrt(da * db)
                corr = 0.0 if denom == 0 else sum(
                    (x - ma) * (y - mb) for x, y in zip(xa, xb)
                ) / denom
            matrix[a][b] = max(-1.0, min(1.0, corr))
    return matrix
