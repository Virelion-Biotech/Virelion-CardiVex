from __future__ import annotations

import argparse
import ast
import csv
import json
import re
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
    """Read the committed module YAML without adding a runtime YAML dependency."""
    text = path.read_text(encoding="utf-8")
    modules: dict[str, tuple[str, ...]] = {}
    current: str | None = None
    for line in text.splitlines():
        module_match = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if module_match:
            current = module_match.group(1)
            continue
        genes_match = re.match(r"^    genes:\s*(\[.*\])\s*$", line)
        if genes_match and current is not None:
            values = ast.literal_eval(genes_match.group(1))
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"invalid gene list for module {current}")
            modules[current] = tuple(values)
    if not modules:
        raise ValueError(f"no gene modules found in {path}")
    return modules


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GSE144424 processed counts for CardiVex.")
    parser.add_argument("--counts", required=True, type=Path)
    parser.add_argument("--sample-map", default=Path("datasets/GSE144424_sample_map.tsv"), type=Path)
    parser.add_argument("--modules", default=Path("configs/gse144424_gene_modules.yaml"), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    matrix = read_geo_counts(args.counts)
    sample_titles = read_sample_map(args.sample_map)
    missing_titles = sorted(set(matrix.sample_ids) - set(sample_titles))
    if missing_titles:
        raise ValueError("count matrix contains unmapped samples: " + ", ".join(missing_titles))
    metadata = parse_gse144424_metadata({sample_id: sample_titles[sample_id] for sample_id in matrix.sample_ids})
    module_config = ModuleScoreConfig(domain_gene_sets=read_modules(args.modules), minimum_genes=3)
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
