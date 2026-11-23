from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(
    os.environ.get("MATH_ASSESSMENT_VERCEL_STAGE", ROOT / ".tmp" / "vercel-stage")
).resolve()
PACKAGED_DATA = Path(
    os.environ.get(
        "MATH_ASSESSMENT_PACKAGED_DATA",
        ROOT / "services" / "math-assessment-api" / "data",
    )
).resolve()

ROOT_FILES = (
    ".vercelignore",
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "vercel.json",
)
ROOT_SCRIPT_FILES = ("strip_next_protection_artifacts.mjs",)
WEB_FILES = (
    "LICENSE",
    "eslint.config.mjs",
    "next-env.d.ts",
    "next.config.ts",
    "package.json",
    "tsconfig.json",
)
API_FILES = ("requirements.txt",)
# Vercel Hobby rejects CLI deployments whose source files exceed 100 MB in total.
UPLOAD_LIMIT_BYTES = 100_000_000


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> None:
    if not TARGET.is_relative_to(ROOT) or TARGET == ROOT:
        raise RuntimeError(f"unsafe Vercel stage target: {TARGET}")
    if TARGET.is_dir():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)
    if not PACKAGED_DATA.is_dir() or not PACKAGED_DATA.is_relative_to(ROOT):
        raise RuntimeError(f"unsafe or missing packaged data source: {PACKAGED_DATA}")

    for name in ROOT_FILES:
        copy_file(ROOT / name, TARGET / name)
    for name in ROOT_SCRIPT_FILES:
        copy_file(ROOT / "scripts" / name, TARGET / "scripts" / name)

    web_source = ROOT / "apps" / "math-assessment-web"
    web_target = TARGET / "apps" / "math-assessment-web"
    shutil.copytree(web_source / "app", web_target / "app")
    if (web_source / "public").is_dir():
        shutil.copytree(web_source / "public", web_target / "public")
    for name in WEB_FILES:
        copy_file(web_source / name, web_target / name)

    api_source = ROOT / "services" / "math-assessment-api"
    api_target = TARGET / "services" / "math-assessment-api"
    # Local test runs leave bytecode caches; they are not deploy inputs.
    shutil.copytree(
        api_source / "app", api_target / "app",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in API_FILES:
        copy_file(api_source / name, api_target / name)
    for source in sorted(PACKAGED_DATA.iterdir()):
        if not source.is_file() or source.suffix in {".sqlite", ".partial"}:
            continue
        copy_file(source, api_target / "data" / source.name)

    files = sorted(path for path in TARGET.rglob("*") if path.is_file())
    oversized = [path for path in files if path.stat().st_size > 4_100_000]
    forbidden = [
        path
        for path in files
        if path.suffix.lower() in {".hwp", ".hwpx", ".pdf", ".sqlite", ".jsonl"}
    ]
    if oversized or forbidden:
        raise RuntimeError(
            "unsafe Vercel stage: "
            f"oversized={[path.name for path in oversized]}, "
            f"forbidden={[path.name for path in forbidden]}"
        )

    total_bytes = sum(path.stat().st_size for path in files)
    if total_bytes > UPLOAD_LIMIT_BYTES:
        raise RuntimeError(
            f"Vercel stage is {total_bytes:,} bytes; Hobby CLI upload limit is "
            f"{UPLOAD_LIMIT_BYTES:,}"
        )

    summary = {
        "target": str(TARGET),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "largest_file_bytes": max(path.stat().st_size for path in files),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
