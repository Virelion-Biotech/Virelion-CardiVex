#!/usr/bin/env python3
"""Download public GEO validation archives and verify their pinned SHA-256."""
from hashlib import sha256
from pathlib import Path
import argparse
import os
import tempfile
from urllib.request import urlopen

ARCHIVES = {
    'GSE144424_Counts_RNA_MCW_NEB.txt.gz': ('GSE144nnn/GSE144424', 'cad9ac4c6514550ea9bfb2b491cc2934f6952894d7cbd17338d5054d03da6f7c'),
    'GSE144423_Counts_ATAC_MCW_NEB.txt.gz': ('GSE144nnn/GSE144423', '44981dcbf23abcd9bed06dd644ff8cfde282473308c983ceddded9c14ed6b33e'),
    'GSE234907_Heart_counts.txt.gz': ('GSE234nnn/GSE234907', 'ee2a2cf4279eefe68aa89aed0251eb192f48f97c48000539f848c9b255752e2c'),
}


def download(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, (series, expected) in ARCHIVES.items():
        target = directory / name
        if target.exists():
            if sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Existing archive checksum mismatch: {name}')
            print(f'Verified {name}')
            continue
        fd, temporary = tempfile.mkstemp(prefix=name + '.', dir=directory)
        try:
            digest = sha256()
            with os.fdopen(fd, 'wb') as output:
                url = f'https://ftp.ncbi.nlm.nih.gov/geo/series/{series}/suppl/{name}'
                with urlopen(url, timeout=120) as response:
                    for chunk in iter(lambda: response.read(1 << 20), b''):
                        digest.update(chunk)
                        output.write(chunk)
            if digest.hexdigest() != expected:
                raise ValueError(f'Download checksum mismatch: {name}')
            os.replace(temporary, target)
            print(f'Downloaded and verified {name}')
        finally:
            Path(temporary).unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'data')
    download(parser.parse_args().directory)
