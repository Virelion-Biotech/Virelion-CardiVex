from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from cardivex.geo_counts import ModuleScoreConfig, parse_gse144424_metadata, read_geo_counts, score_count_modules


def read_sample_map(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        result = {row["sample_id"]: row["title"] for row in rows}
    if len(result) != 84:
        raise ValueError(f"expected 84 GSE144424 sample mappings, found {len(result)}")
    return result


def read_modules(path: Path) -> dict[str, tuple[str, ...]]:
    # Keep this runner dependency-light: the committed module file is mirrored
    # here as an explicit JSON-like YAML-compatible structure in code review.
    # Users can replace it only through a deliberate code/config change.
    return {
        "hypoxia_response": ("HIF1A", "VEGFA", "EGLN3", "LDHA", "SLC2A1", "BNIP3", "ADM"),
        "inflammatory_response": ("IL6", "CXCL8", "CCL2", "NFKBIA", "TNFAIP3", "PTGS2", "ICAM1"),
        "stress_response": ("DDIT3", "ATF4", "HSPA5", "XBP1", "DNAJB9", "HMOX1"),
        "contractile_maturation": ("TNNT2", "TNNI3", "MYH6", "MYH7", "ACTC1", "RYR2", "ATP2A2"),
        "extracellular_matrix_remodeling": ("COL1A1", "COL1A2", "COL3A1", "FN1", "TGFB1", "SERPINE1", "MMP2"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GSE144424 processed counts for CardiVex.")
    parser.add_argument("--counts", required=True, type=Path)
    parser.add_argument("--sample-map", default=Path("datasets/GSE144424_sample_map.tsv"), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    matrix = read_geo_counts(args.counts)
    sample_titles = read_sample_map(args.sample_map)
    metadata = parse_gse144424_metadata({sample_id: sample_titles[sample_id] for sample_id in matrix.sample_ids})
    module_config = ModuleScoreConfig(domain_gene_sets=read_modules(Path("configs/gse144424_gene_modules.yaml")), minimum_genes=3)
    records = score_count_modules(matrix, metadata, module_config)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_id": "GSE144424",
        "source": "NCBI GEO processed count matrix",
        "record_count": len(records),
        "records": [
            {
                "observation_id": record.observation_id,
                "condition": record.condition,
                "time": record.time,
                "state": record.state.domain_scores,
                "provenance": record.provenance,
            }
            for record in records
        ],
    }
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    print(f"wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
