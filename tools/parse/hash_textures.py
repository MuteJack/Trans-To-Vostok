"""
Hashing primitives for recovered PCK textures.

A thin library used by:
    - parse_textures.py    (writes the sha256 column into textures.tsv)
    - future diff_textures (reads textures.tsv snapshots; may re-hash files
                            if pixel-data verification is needed later)

PCK extraction is deterministic on Road to Vostok 0.1.1.3 (verified across
gdre_tools 2.4.0 and 2.5.0-beta5 — bit-identical output), so a byte SHA-256
of the recovered PNG is sufficient. If a future gdre_tools build introduces
PNG re-encoding variance (tIME chunk, zlib level, etc.), swap sha256_of for
a pixel-data hash via Pillow.
"""
import hashlib
from pathlib import Path


TEXTURE_EXTENSIONS = {".png"}
HASH_CHUNK = 65536


def sha256_of(path: Path) -> str:
    """Hex SHA-256 of a file streamed in HASH_CHUNK-sized chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
