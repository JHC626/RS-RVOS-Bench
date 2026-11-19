"""Check v1.0 split membership, indexed PNGs, track visibility and release counts."""
import csv
import gzip
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify():
    meta = json.loads((ROOT / "annotations.json").read_text(encoding="utf-8"))
    videos = meta["videos"]
    stats = json.loads((ROOT / "stats.json").read_text())
    splits = {}
    for split in ("train", "test"):
        listed = (ROOT / "splits" / f"{split}.txt").read_text().splitlines()
        splits[split] = set(listed)
        require(len(listed) == len(splits[split]), f"Duplicate entry in {split}")
    require(not splits["train"] & splits["test"], "Overlapping video IDs")
    require(splits["train"] | splits["test"] == set(videos), "Incomplete splits")
    with gzip.open(ROOT / "frames.tsv.gz", "rt", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    index = {(r["video"], r["frame"]): r for r in rows}
    expected = {(v, f) for v, data in videos.items() for f in data["frames"]}
    require(len(index) == len(rows) and set(index) == expected, "Frame index differs")
    categories = set()
    hashes = {s: set() for s in splits}
    fields = ("videos", "frames", "tracks", "expressions", "instance_frames", "referred_instance_frames")
    counts = {s: dict.fromkeys(fields, 0) for s in splits}
    with zipfile.ZipFile(ROOT / "masks.zip") as archive:
        names = archive.namelist()
        require(len(names) == len(expected) and set(names) == {f"masks/{v}/{f}.png" for v,f in expected}, "Mask inventory differs")
        for video, data in videos.items():
            split = data["split"]
            require(video in splits[split], f"Incorrect split for {video}")
            frames, objects, refs = data["frames"], data["objects"], data["expressions"]
            require(frames and frames == sorted(set(frames)) and refs, f"Empty or invalid record: {video}")
            visible = defaultdict(set)
            for oid, obj in objects.items():
                categories.add(obj["category"])
                record = obj["frames"]
                require(len(set(record)) == len(record) and set(record) <= set(frames), f"Invalid track: {video}/{oid}")
                for frame in record:
                    visible[frame].add(int(oid))
            for ref in refs.values():
                require(ref["exp"].strip() and int(ref["obj_id"]) in visible[frames[0]], f"Invalid reference: {video}")
            c = counts[split]
            c["videos"] += 1
            c["frames"] += len(frames)
            c["tracks"] += len(objects)
            c["expressions"] += len(refs)
            c["instance_frames"] += sum(len(o["frames"]) for o in objects.values())
            c["referred_instance_frames"] += sum(len(objects[r["obj_id"]]["frames"]) for r in refs.values())
            for frame in frames:
                row = index[video, frame]
                hashes[split].add(row["image_sha256"])
                data_bytes = archive.read(f"masks/{video}/{frame}.png")
                require(hashlib.sha256(data_bytes).hexdigest() == row["mask_sha256"], f"Changed mask: {video}/{frame}")
                with Image.open(io.BytesIO(data_bytes)) as mask:
                    require(mask.mode in ("P", "L"), f"Unexpected mask encoding: {video}/{frame}")
                    labels = {i for i,n in enumerate(mask.histogram()) if n and i not in (0,255)}
                require(labels == visible[frame], f"Track IDs differ from pixels: {video}/{frame}")
    require(not hashes["train"] & hashes["test"], "Identical encoded image across splits")
    require(set(meta["categories"]) == categories, "Category list differs")
    counts["all"] = {field: sum(counts[s][field] for s in splits) for field in fields}
    require(counts == stats, "Statistics differ")
    print(f'Verified {counts["all"]["videos"]} videos, {len(index)} masks and {counts["all"]["expressions"]} expressions.')


if __name__ == "__main__":
    verify()
