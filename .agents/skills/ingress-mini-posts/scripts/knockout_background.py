#!/usr/bin/env python3
"""
knockout_background.py

Removes backgrounds from miniature token photos, produces transparent PNG/WebP images,
and crops them neatly to the subject's bounding box with a configurable margin.

Usage:
    python3 knockout_background.py [options] [files ...]

Examples:
    # Process all images in ingress/ directory to PNG
    python3 knockout_background.py --input-dir ingress/ --output-dir ingress/

    # Process specific files and output to target directory
    python3 knockout_background.py ingress/BlackDrake1.jpg --output-dir assets/images/minis/dragons/

Requirements:
    pip install "rembg[cpu]" pillow
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from PIL import Image

try:
    import rembg
except ImportError:
    rembg = None


_worker_session = None

def get_session(model_name="u2net"):
    global _worker_session
    if _worker_session is None and rembg is not None:
        _worker_session = rembg.new_session(model_name=model_name)
    return _worker_session


def process_image(in_path, out_path, margin=10, out_format="PNG", model_name="u2net"):
    t0 = time.time()
    if rembg is None:
        raise RuntimeError("rembg is not installed. Please run: pip install 'rembg[cpu]' pillow")

    session = get_session(model_name)
    inp = Image.open(in_path)
    out = rembg.remove(inp, session=session)

    bbox = out.getbbox()
    if bbox:
        crop_box = (
            max(0, bbox[0] - margin),
            max(0, bbox[1] - margin),
            min(out.width, bbox[2] + margin),
            min(out.height, bbox[3] + margin),
        )
        out = out.crop(crop_box)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    save_kwargs = {}
    if out_format.upper() == "PNG":
        save_kwargs["optimize"] = True
    elif out_format.upper() == "WEBP":
        save_kwargs["quality"] = 90

    out.save(out_path, format=out_format.upper(), **save_kwargs)
    duration = time.time() - t0
    print(f"Processed '{in_path}' -> '{out_path}' ({out.size[0]}x{out.size[1]}) in {duration:.2f}s")
    return out_path


def _worker_task(args):
    in_path, out_path, margin, out_format, model_name = args
    return process_image(in_path, out_path, margin=margin, out_format=out_format, model_name=model_name)


def main():
    parser = argparse.ArgumentParser(
        description="Remove backgrounds from miniature images and crop to transparent bounding box."
    )
    parser.add_argument("files", nargs="*", help="Specific image files to process.")
    parser.add_argument(
        "--input-dir",
        "-i",
        default=None,
        help="Input directory containing images (e.g. ingress/).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Output directory for processed images. Defaults to same as input or current dir.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["png", "webp", "PNG", "WEBP"],
        default="png",
        help="Output image format (png or webp). Default: png.",
    )
    parser.add_argument(
        "--margin",
        "-m",
        type=int,
        default=10,
        help="Transparent margin in pixels around bounding box. Default: 10.",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=2,
        help="Number of concurrent worker processes. Default: 2.",
    )
    parser.add_argument(
        "--model",
        default="u2net",
        help="Rembg model name (e.g. u2net, isnet-general-use). Default: u2net.",
    )

    args = parser.parse_args()

    if rembg is None:
        sys.stderr.write("Error: 'rembg' package is not installed.\n")
        sys.stderr.write("Install with: pip install 'rembg[cpu]' pillow\n")
        sys.exit(1)

    target_files = []
    if args.files:
        target_files.extend(args.files)

    if args.input_dir:
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        for fname in sorted(os.listdir(args.input_dir)):
            if fname.startswith("."):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in valid_exts:
                target_files.append(os.path.join(args.input_dir, fname))

    if not target_files:
        print("No image files found or specified.")
        sys.exit(0)

    target_ext = f".{args.format.lower()}"
    tasks = []
    for in_path in target_files:
        base = os.path.splitext(os.path.basename(in_path))[0]
        out_name = f"{base}{target_ext}"
        if args.output_dir:
            out_path = os.path.join(args.output_dir, out_name)
        else:
            out_path = os.path.join(os.path.dirname(in_path), out_name)
        tasks.append((in_path, out_path, args.margin, args.format, args.model))

    print(f"Starting background removal for {len(tasks)} file(s) with {args.workers} worker(s)...")
    t_start = time.time()

    if args.workers <= 1:
        for t in tasks:
            _worker_task(t)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            list(executor.map(_worker_task, tasks))

    print(f"All images completed in {time.time() - t_start:.2f}s.")


if __name__ == "__main__":
    main()
