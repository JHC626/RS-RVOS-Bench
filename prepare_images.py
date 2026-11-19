"""Match locally held SAT-MTB images and export the verified reference JPEGs."""
import argparse
import csv
import gzip
import hashlib
import io
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent

# The reference images for these two videos were cropped from quality-95 JPEGs.
CROPS = {"airplane_51": (0, 0, 770, 800), "ship_09": (0, 100, 600, 600)}


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(data)
            f.close()
            if path.exists():
                if path.read_bytes() != data:
                    raise FileExistsError(f"Conflicting image: {path}")
            else:
                os.replace(temporary, path)
        finally:
            f.close()
            temporary.unlink(missing_ok=True)


def export_video(source, output, video, rows):
    pending = defaultdict(list)
    dest = output / video
    dest.mkdir(parents=True, exist_ok=True)
    for row in rows:
        path = dest / (row["frame"] + ".jpg")
        if path.exists():
            if fingerprint(path.read_bytes()) != row["image_sha256"]:
                raise FileExistsError(f"Conflicting image: {path}")
        else:
            pending[row["image_sha256"]].append(path)
    category, number = video.split("_", 1)
    folder = source / category / number / "img"
    if not folder.is_dir():
        folder = source / video
    for path in sorted(folder.glob("*")):
        if not pending:
            break
        if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        data = path.read_bytes()
        digest = fingerprint(data)
        if digest not in pending:
            with Image.open(io.BytesIO(data)) as image:
                encoded = io.BytesIO()
                image.convert("RGB").save(encoded, "JPEG", quality=95)
            data = encoded.getvalue()
            digest = fingerprint(data)
            if digest not in pending and video in CROPS:
                with Image.open(io.BytesIO(data)) as jpeg:
                    cropped = io.BytesIO()
                    jpeg.crop(CROPS[video]).save(cropped, "JPEG", quality=75)
                data = cropped.getvalue()
                digest = fingerprint(data)
        for target in pending.pop(digest, []):
            write_new(target, data)
    return sorted(p.name for paths in pending.values() for p in paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--video", help="Process a single video ID")
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error("Image source directory does not exist")
    records = defaultdict(list)
    with gzip.open(ROOT / "frames.tsv.gz", "rt", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if args.video is None or row["video"] == args.video:
                records[row["video"]].append(row)
    if not records:
        parser.error("No matching video in the release")
    missing = 0
    for video, rows in records.items():
        unmatched = export_video(args.source, args.output, video, rows)
        print(f"{video}: {len(rows)-len(unmatched)}/{len(rows)} frames verified", flush=True)
        if unmatched:
            print("Unmatched frame names:", ", ".join(unmatched))
        missing += len(unmatched)
    return bool(missing)


if __name__ == "__main__":
    raise SystemExit(main())
