#!/usr/bin/env bash
# NASA image assets shipped into the static GitHub Pages artifact.
# Sources: https://svs.gsfc.nasa.gov/2915 and https://svs.gsfc.nasa.gov/2916
set -euo pipefail

hud_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image_dir="${hud_dir}"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

fetch_png() {
  local source="$1" target="$2"
  curl --fail --silent --show-error --location \
    --proto '=https' --tlsv1.2 \
    --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 100 \
    "${source}" --output "${tmp_dir}/${target}"
}

fetch_png 'https://svs.gsfc.nasa.gov/vis/a000000/a002900/a002915/bluemarble-1024.png' 'earth-blue-marble.png'
fetch_png 'https://svs.gsfc.nasa.gov/vis/a000000/a002900/a002916/earthatnight-2048.png' 'earth-night.png'

python3 - "${tmp_dir}" <<'PY'
import pathlib
import struct
import sys

root = pathlib.Path(sys.argv[1])
for file_name, expected in (
    ("earth-blue-marble.png", (1024, 512)),
    ("earth-night.png", (2048, 1024)),
):
    source = root / file_name
    if not source.is_file():
        raise SystemExit(f"Missing texture: {file_name}")
    with source.open("rb") as stream:
        hdr = stream.read(24)
    if len(hdr) < 24 or hdr[:8] != bytes((137, 80, 78, 71, 13, 10, 26, 10)) or hdr[12:16] != b"IHDR":
        raise SystemExit(f"Invalid PNG signature: {file_name}")
    actual = struct.unpack(">II", hdr[16:24])
    if actual != expected:
        raise SystemExit(f"Unexpected dimensions in {file_name}: {actual}")
    size = source.stat().st_size
    if size < 30_000 or size > 4_000_000:
        raise SystemExit(f"Unexpected PNG size in {file_name}: {size}")
    print(f"NASA texture verified: {file_name} ({actual[0]}x{actual[1]}, {size} bytes)")
PY

mv "${tmp_dir}/earth-blue-marble.png" "${image_dir}/earth-blue-marble.png"
mv "${tmp_dir}/earth-night.png" "${image_dir}/earth-night.png"
