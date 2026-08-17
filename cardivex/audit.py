from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class AuditRecord:
    run_id: str
    scenario_id: str
    scenario_version: str
    model_version: str
    feature_pipeline_version: str
    config: dict[str, Any]
    seed: int | None
    input_digest: str
    created_at: str


def digest_payload(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(canonical).hexdigest()


def build_audit_record(
    *,
    run_id: str,
    scenario_id: str,
    scenario_version: str,
    model_version: str,
    feature_pipeline_version: str,
    config: dict[str, Any],
    seed: int | None,
    input_payload: Any,
) -> dict[str, Any]:
    record = AuditRecord(
        run_id=run_id,
        scenario_id=scenario_id,
        scenario_version=scenario_version,
        model_version=model_version,
        feature_pipeline_version=feature_pipeline_version,
        config=config,
        seed=seed,
        input_digest=digest_payload(input_payload),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return asdict(record)
