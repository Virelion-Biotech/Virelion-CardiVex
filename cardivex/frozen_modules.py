from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence

from .geo_counts import ModuleScoreConfig, ModuleScoreScaler


@dataclass(frozen=True)
class FrozenModuleTransform:
    """Immutable representation of a fitted module transform."""

    artifact_version: str
    dataset_id: str
    source_file: str
    source_sha256: str
    normalization: str
    minimum_genes: int
    domain_gene_sets: Mapping[str, tuple[str, ...]]
    centers: Mapping[str, float]
    scales: Mapping[str, float]
    fit_sample_ids: tuple[str, ...]
    artifact_id: str

    def payload(self) -> dict[str, object]:
        return {
            "artifact_version": self.artifact_version,
            "dataset_id": self.dataset_id,
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "normalization": self.normalization,
            "minimum_genes": self.minimum_genes,
            "domain_gene_sets": {domain: list(genes) for domain, genes in sorted(self.domain_gene_sets.items())},
            "centers": {domain: float(value) for domain, value in sorted(self.centers.items())},
            "scales": {domain: float(value) for domain, value in sorted(self.scales.items())},
            "fit_sample_ids": list(self.fit_sample_ids),
        }

    def to_dict(self) -> dict[str, object]:
        return self.payload() | {"artifact_id": self.artifact_id}

    def validate_config(self, config: ModuleScoreConfig) -> None:
        expected = {domain: tuple(genes) for domain, genes in config.domain_gene_sets.items()}
        if expected != dict(self.domain_gene_sets):
            raise ValueError("frozen artifact gene sets do not match scoring config")
        if int(config.minimum_genes) != self.minimum_genes:
            raise ValueError("frozen artifact minimum_genes does not match scoring config")

    def apply(self, raw_scores: Sequence[Mapping[str, float]]) -> tuple[dict[str, float], ...]:
        domains = tuple(sorted(self.domain_gene_sets))
        missing = [domain for domain in domains if domain not in self.centers or domain not in self.scales]
        if missing:
            raise ValueError("frozen artifact is incomplete for domains: " + ", ".join(missing))
        return tuple(
            {
                domain: max(
                    0.0,
                    min(1.0, 0.5 + 0.15 * (float(row[domain]) - float(self.centers[domain])) / float(self.scales[domain])),
                )
                for domain in domains
            }
            for row in raw_scores
        )


def compute_artifact_id(
    *,
    dataset_id: str,
    source_file: str,
    source_sha256: str,
    normalization: str,
    minimum_genes: int,
    domain_gene_sets: Mapping[str, Sequence[str]],
    scaler: ModuleScoreScaler,
    artifact_version: str = "0.2.0",
) -> str:
    payload = {
        "artifact_version": artifact_version,
        "dataset_id": dataset_id,
        "source_file": source_file,
        "source_sha256": source_sha256,
        "normalization": normalization,
        "minimum_genes": minimum_genes,
        "domain_gene_sets": {domain: list(genes) for domain, genes in sorted(domain_gene_sets.items())},
        "centers": {domain: float(value) for domain, value in sorted(scaler.centers.items())},
        "scales": {domain: float(value) for domain, value in sorted(scaler.scales.items())},
        "fit_sample_ids": list(scaler.fit_sample_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def freeze_module_transform(
    config: ModuleScoreConfig,
    scaler: ModuleScoreScaler,
    *,
    dataset_id: str,
    source_file: str,
    source_sha256: str,
    normalization: str = "log1p(CPM) then development-only z-standardization and 0.15 scaling around 0.5",
    artifact_version: str = "0.2.0",
) -> FrozenModuleTransform:
    config_domains = {domain: tuple(genes) for domain, genes in config.domain_gene_sets.items()}
    artifact_id = compute_artifact_id(
        dataset_id=dataset_id,
        source_file=source_file,
        source_sha256=source_sha256,
        normalization=normalization,
        minimum_genes=config.minimum_genes,
        domain_gene_sets=config_domains,
        scaler=scaler,
        artifact_version=artifact_version,
    )
    return FrozenModuleTransform(
        artifact_version=artifact_version,
        dataset_id=dataset_id,
        source_file=source_file,
        source_sha256=source_sha256,
        normalization=normalization,
        minimum_genes=config.minimum_genes,
        domain_gene_sets=config_domains,
        centers=dict(scaler.centers),
        scales=dict(scaler.scales),
        fit_sample_ids=tuple(scaler.fit_sample_ids),
        artifact_id=artifact_id,
    )


def frozen_module_transform_json(artifact: FrozenModuleTransform) -> str:
    return json.dumps(artifact.to_dict(), sort_keys=True, indent=2)


def require_complete_frozen_transform(artifact: FrozenModuleTransform) -> None:
    if not artifact.centers or not artifact.scales:
        raise ValueError("frozen module transform is incomplete: fitted centers/scales are required")
    if set(artifact.centers) != set(artifact.domain_gene_sets) or set(artifact.scales) != set(artifact.domain_gene_sets):
        raise ValueError("frozen module transform is incomplete: every domain needs a center and scale")
