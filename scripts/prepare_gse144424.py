from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from pathlib import Path

from cardivex.geo_counts import ModuleScoreConfig, read_geo_counts, score_count_modules
from cardivex.geo_metadata import parse_gse144424_count_column, parse_gse144424_sample_title


def read_sample_map(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        result = {row["sample_id"]: row["title"] for row in rows}
    if len(result) != 84:
        raise ValueError(f"expected 84 GSE144424 sample mappings, found {len(result)}")
    return result


def read_modules(path: Path, *, prefer_ensembl: bool = False) -> dict[str, tuple[str, ...]]:
    """Read committed module YAML without adding a runtime YAML dependency."""
    text = path.read_text(encoding="utf-8")
    modules: dict[str, tuple[str, ...]] = {}
    current: str | None = None
    for line in text.splitlines():
        module_match = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if module_match:
            current = module_match.group(1)
            continue
        if prefer_ensembl:
            ensembl_match = re.match(r"^    ensembl:\s*\[(.*)\]\s*$", line)
            if ensembl_match and current is not None:
                values = [item.strip().strip("'\"") for item in ensembl_match.group(1).split(",") if item.strip()]
                modules[current] = tuple(values)
                continue
        genes_match = re.match(r"^    genes:\s*(\[.*\])\s*$", line)
        if genes_match and current is not None:
            raw = genes_match.group(1)
            try:
                values = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                # Unquoted symbol lists: [HIF1A, VEGFA, ...]
                inner = raw.strip()[1:-1]
                values = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"invalid gene list for module {current}")
            modules[current] = tuple(values)
            continue
        symbols_match = re.match(r"^    symbols:\s*\[(.*)\]\s*$", line)
        if symbols_match and current is not None and not prefer_ensembl:
            values = [item.strip().strip("'\"") for item in symbols_match.group(1).split(",") if item.strip()]
            modules[current] = tuple(values)
    if not modules:
        raise ValueError(f"no gene modules found in {path}")
    return modules


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GSE144424 processed counts for CardiVex.")
    parser.add_argument("--counts", required=True, type=Path)
    parser.add_argument("--sample-map", default=Path("datasets/GSE144424_sample_map.tsv"), type=Path)
    parser.add_argument(
        "--modules",
        default=Path("configs/gse144424_ensembl_modules.yaml"),
        type=Path,
        help="Module YAML (prefer ensembl IDs for the published count matrix)",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--id-mode",
        choices=("auto", "count-column", "sample-map"),
        default="auto",
        help="How to interpret sample identifiers in the count matrix",
    )
    args = parser.parse_args()

    matrix = read_geo_counts(args.counts)
    id_mode = args.id_mode
    if id_mode == "auto":
        id_mode = "count-column" if all(sid.startswith("H") for sid in matrix.sample_ids) else "sample-map"

    if id_mode == "count-column":
        metadata = [parse_gse144424_count_column(sample_id) for sample_id in matrix.sample_ids]
        prefer_ensembl = True
    else:
        sample_titles = read_sample_map(args.sample_map)
        missing_titles = sorted(set(matrix.sample_ids) - set(sample_titles))
        if missing_titles:
            raise ValueError("count matrix contains unmapped samples: " + ", ".join(missing_titles))
        metadata = [
            parse_gse144424_sample_title(sample_id, sample_titles[sample_id])
            for sample_id in matrix.sample_ids
        ]
        prefer_ensembl = False

    module_config = ModuleScoreConfig(
        domain_gene_sets=read_modules(args.modules, prefer_ensembl=prefer_ensembl),
        minimum_genes=3,
    )
    records = score_count_modules(matrix, metadata, module_config)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_id": "GSE144424",
        "source": "NCBI GEO processed count matrix",
        "id_mode": id_mode,
        "record_count": len(records),
        "records": [
            {
                "observation_id": record.observation_id,
                "condition": record.condition,
                "time": record.time,
                "state": dict(record.state.domain_scores),
                "source_ref": record.source_ref,
                "metadata": dict(record.state.metadata),
            }
            for record in records
        ],
    }
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    print(f"wrote {len(records)} records to {args.output} (id_mode={id_mode})")


if __name__ == "__main__":
    main()
