from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .ingest import IngestRecord


@dataclass(frozen=True)
class QualityIssue:
    code: str
    observation_id: str | None
    message: str
    severity: str = "error"


def inspect_records(records: Iterable[IngestRecord]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    seen: set[str] = set()
    for record in records:
        if record.observation_id in seen:
            issues.append(QualityIssue("DUPLICATE_OBSERVATION", record.observation_id, "observation ID appears more than once"))
        seen.add(record.observation_id)
        if not record.source_ref:
            issues.append(QualityIssue("MISSING_SOURCE", record.observation_id, "observation has no source reference", "warning"))
        if not record.available_modalities:
            issues.append(QualityIssue("NO_MODALITY", record.observation_id, "observation contains no processed modality"))
        if not record.state.domain_scores:
            issues.append(QualityIssue("NO_DOMAIN_SCORES", record.observation_id, "observation has no domain scores", "warning"))
    return issues


def require_clean(records: Iterable[IngestRecord]) -> None:
    issues = inspect_records(records)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        message = "; ".join(f"{issue.code}: {issue.message}" for issue in errors)
        raise ValueError(message)
