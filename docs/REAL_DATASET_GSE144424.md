# First real-data benchmark candidate: GSE144424 / GSE144426

CardiVex's first real-data candidate is the Ward/Banovich hypoxia-reoxygenation iPSC-cardiomyocyte study.

GSE144424 contains RNA-seq from human iPSC-derived cardiomyocytes from 15 individuals under four matched conditions: normoxia, 6-hour hypoxia, 6-hour reoxygenation after hypoxia, and 24-hour reoxygenation after hypoxia. The GEO record reports 84 RNA-seq samples because three individuals were replicated three times. The experimental unit for CardiVex is therefore the subject, not the individual RNA sample. citehttps://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE144424

The companion GSE144426 SuperSeries contains matched ATAC-seq and methylation subseries in addition to the RNA-seq data, making it unusually useful for testing regulatory-state consistency across modalities. citehttps://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE144426

## CardiVex mapping

| Code | Condition | Derived elapsed time |
|---|---|---:|
| A | normoxia | 0 h |
| B | hypoxia | 6 h |
| C | reoxygenation 1 | 12 h |
| D | reoxygenation 2 | 30 h |

The elapsed-time mapping is a derived analysis field; the original condition labels remain preserved.

## What this dataset is good for

- Empirical phenotype calibration from a controlled cardiac stress response.
- Longitudinal trajectory calibration.
- Cross-subject generalization.
- Correlation-aware challenge generation.
- Temporal-shift benchmarking.
- Cross-modal regulatory-state validation using RNA/ATAC/methylation.

## What it does not provide

It is not an organoid imaging dataset and does not provide direct morphology/function measurements in the GEO record. Therefore CardiVex should not manufacture imaging or functional measurements from this study. Those modalities should be supplied by a separate matched dataset or treated as unavailable.

A complementary organoid dataset is GSE234907, which contains human vascularized cardiac organoids with simultaneous oxygen-uptake, extracellular-field-potential, and contraction sensing, plus RNA-seq. It is useful as a future functional/organoid validation companion, but its experimental design is not a subject-level hypoxia/reoxygenation longitudinal dataset like GSE144424. citehttps://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE234907

## First split policy

All A/B/C/D measurements from a subject must remain in the same development or held-out partition. Replicate sample suffixes such as `18511_2_A_RNA-seq` and `18511_3_A_RNA-seq` remain part of subject `18511` and may not be split independently.

The first validation design should hold out complete subjects, not individual samples or time points.
