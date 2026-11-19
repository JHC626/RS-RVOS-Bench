# RS-RVOS Bench v1.0

[Project page (English)](https://jhc626.github.io/RS-RVOS-Bench/) · [中文项目页](https://jhc626.github.io/RS-RVOS-Bench/zh/)

Satellite-video referring object segmentation annotations for SAT-MTB. Each expression identifies a target visible in the first frame. A target keeps the same instance ID throughout its video. This is a single annotation release with a fixed video-level train/test split. Users supply the SAT-MTB source frames.

| Split | Videos | Frames | Tracks | Expressions | Visible instance-frames |
|---|---:|---:|---:|---:|---:|
| Train | 79 | 18,557 | 720 | 702 | 170,581 |
| Test | 29 | 5,809 | 194 | 189 | 39,468 |
| Total | 108 | 24,366 | 914 | 891 | 210,049 |

An instance-frame is one unique combination of video, object ID and visible frame. The 891 expressions cover 206,387 instance-frames. The masks contain 11 fine-grained object classes. Use `(video_id, expression_id)` as the sample key. Some targets in the same scene share a description, and some tracks have no first-frame expression.

## Files

| File | Contents |
|---|---|
| `splits/train.txt`, `splits/test.txt` | Authoritative video IDs for v1.0, one per line |
| `annotations.json` | Per-video frame order, split, objects, visibility lists and referring expressions |
| `masks.zip` | One indexed PNG per frame at `masks/<video>/<frame>.png` |
| `frames.tsv.gz` | SHA-256 of the reference JPEG and mask for each video/frame pair |
| `stats.json` | Machine-readable split totals |
| `prepare_images.py`, `verify.py` | Match source images and check the distributed annotations |

## Quick start

Download SAT-MTB from its official project page and extract its aircraft and ship images. Set `--source` to the directory containing the `airplane/` and `ship/` folders. The RS-RVOS annotations, instance masks and split lists are included here. [SAT-MTB official download page](https://csu.cas.cn/gb/kybm/sjlyzx/gcxx_sjj/sjj_wxxl/202211/t20221121_6551405.html)

From the unpacked RS-RVOS repository, with Python 3.10 or newer:

```sh
python -m pip install Pillow
python verify.py
python prepare_images.py --source /path/to/SAT-MTB_Dataset --output images
```

After all 24,366 frames match, use `splits/train.txt` and `splits/test.txt` with `images/<video>/<frame>.jpg` and the same frame ID in `masks.zip`. The matching script returns exit code 0 on success. If it reports unresolved frames, check the SAT-MTB folder layout and use the original downloaded frames without resizing or re-encoding.

The image source can contain `airplane/<number>/img/` and `ship/<number>/img/`, or reference JPEGs under `<video_id>/`. To check one video, add `--video airplane_47`. The program matches by content and writes `images/<video>/<frame>.jpg` only on an exact SHA-256 match. It converts source PNGs to quality-95 JPEGs. For airplane_51 it retains the leftmost 770 columns, and for ship_09 it removes the top 100 rows. These two crops are applied to the decoded quality-95 JPEG and saved at quality 75 to reproduce the reference files. If a source collection differs, the command lists unresolved frame IDs and returns a nonzero exit status. Re-running after supplying the matching files resumes from verified output.

Read a target mask directly from the archive:

```python
import io
import json
import zipfile
from pathlib import Path
from PIL import Image

videos = json.loads(Path("annotations.json").read_text(encoding="utf-8"))["videos"]
video_id = Path("splits/test.txt").read_text().splitlines()[0]
video = videos[video_id]
expression = next(iter(video["expressions"].values()))
frame = video["frames"][0]
object_id = int(expression["obj_id"])
with zipfile.ZipFile("masks.zip") as masks:
    with Image.open(io.BytesIO(masks.read(f"masks/{video_id}/{frame}.png"))) as mask:
        target = Image.frombytes("L", mask.size, mask.tobytes()).point(
            lambda pixel: 255 if pixel == object_id else 0
        )
print(video_id, frame, expression["exp"], target.getbbox())
```

PNG values encode background as 0 and foreground as the integer object ID. Read the stored indices before converting a palette image to RGB. To extract all masks to disk, run `python -m zipfile -e masks.zip .`.

## Relationship to the paper

The manuscript reports 111 sequence entries and an 82/29 split. **v1.0 uses 108 videos and a new, fixed 79/29 split.** The test set retains the 29 source-video IDs from the archived inference inputs. Every other retained video belongs to training. An exhaustive comparison found zero identical decoded RGB frames across the two splits. Experiments using v1.0 should report these splits and evaluate the 189 test expressions.

The manuscript's archived main-table run scored 44 targets from 28 source videos. Its J&F of 0.712 belongs to that historical protocol. A v1.0 score requires training and evaluation on the split distributed here.

Three historical entries were excluded. `ship_08_copy` duplicates part of `ship_08` with a 44-frame image/mask offset. All 325 frames in `ship_07` also occur in the 326-frame `ship_55`; v1.0 retains the scored sequence `ship_07`. `airplane_62` has no referring expression. The release keeps the 295 available labeled frames in `ship_29` and the 197 indexed pairs in `ship_04`. Repeated occurrences of the same frame ID within an object's visibility list count once. Historical expression wording is preserved.

## 中文发布说明

本包是唯一的正式标注版本。固定划分为 **79 个训练视频、29 个测试视频**；已有 SAT-MTB 原图的用户可用配套脚本按哈希配对。共 24,366 对帧和掩码，891 条指代表达，11 个细类。测试集的 189 条表达均指向首帧可见的目标。

整理时保留了历史推理覆盖的 29 个测试视频，排除了错位副本、与测试视频重复的序列，以及没有指代表达的序列。训练与测试之间的视频 ID、逐帧 JPEG 哈希和解码后的 RGB 图像均无重复。论文主表的 0.712 是历史 44 个目标上的结果；引用本发布版时请使用 v1.0 的实际规模和划分。

## Citation and source data

Please cite the RS-RVOS Bench paper and the upstream SAT-MTB dataset.

Haochen Jiang et al., *CroBIM-V: Memory-Quality Controlled Remote Sensing Referring Video Object Segmentation*, IEEE Transactions on Geoscience and Remote Sensing, 2026. [IEEE Xplore](https://ieeexplore.ieee.org/document/11457059) · [Paper DOI](https://doi.org/10.1109/TGRS.2026.3678310)

```bibtex
@article{jiang2026crobimv,
  author  = {Jiang, Haochen and Sun, Yuzhe and Dong, Zhe and Liu, Tianzhu and Gu, Yanfeng},
  title   = {{CroBIM-V}: Memory-Quality Controlled Remote Sensing Referring Video Object Segmentation},
  journal = {IEEE Transactions on Geoscience and Remote Sensing},
  year    = {2026},
  volume  = {64},
  pages   = {1--16},
  doi     = {10.1109/TGRS.2026.3678310}
}
```

Shengyang Li et al., *A Multitask Benchmark Dataset for Satellite Video: Object Detection, Tracking, and Segmentation*, IEEE Transactions on Geoscience and Remote Sensing, 2023. [SAT-MTB dataset page](https://csu.cas.cn/gb/kybm/sjlyzx/gcxx_sjj/sjj_wxxl/202211/t20221121_6551405.html) · [Paper DOI](https://doi.org/10.1109/TGRS.2023.3278075)
