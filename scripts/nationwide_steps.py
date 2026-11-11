"""Build nationwide round, publication and gate commands without running them.

Run .venv/Scripts/python.exe scripts/run_nationwide.py --help.
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from scripts.science_catalog_inputs import DEFAULT_ROUNDS

# M2(2026-11-11): 규칙이 확실한 카드는 활동 AI를 부르지 않는다. 비우면 예전 동작(카드마다 AI).
AXES_TARGET_EXTRA = ("--per-card", "--skip-rule-confident")
OUTPUT = Path("data/derived/nationwide")
DATABASE = "data/publish/science/math_assessment_catalog_detail.sqlite"
PUBLIC_DATABASE = "data/publish/science/math_assessment_catalog_detail.public.sqlite"
API_URL = "http://127.0.0.1:8012"
WEB_URL = "http://127.0.0.1:3102"
ROUND_ORDER = (3, 1)
DEFAULT_MODEL = "gpt-6.1-terra"
DEFAULT_WORKERS = 8
MAX_WORKERS = 12
DEFAULT_WAIT_SECONDS = 3600
AI_OK_CODES = (0, 3)
DEFAULT_ISOLATED_CWD = Path("C:/Users/USER/codex-isolated/math-n1-8")
CODEX_PATTERN = "C:/Users/USER/AppData/Local/OpenAI/Codex/bin/*/codex.exe"
ROUND_COLUMNS = (
    "school_id", "school_name", "region_sido", "region_sgg", "school_code",
    "neis_school_code", "education_office_code", "school_kind", "shl_idf_cd",
)


@dataclass(frozen=True)
class Config:
    root: Path
    bundles: tuple[int, ...] = (1,)
    model: str = DEFAULT_MODEL
    workers: int = DEFAULT_WORKERS
    isolated_cwd: Path = DEFAULT_ISOLATED_CWD
    wait_seconds: float = DEFAULT_WAIT_SECONDS
    sequential_rounds: bool = False


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]
    ok_codes: tuple[int, ...] = (0,)
    kind: str = "command"
    env: dict[str, str] = field(default_factory=dict)
    cwd: Path = Path(".")


def child_env(model: str, extra: dict | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.update(extra or {})
    env.update(PYTHONIOENCODING="utf-8", MIDDLE_AI_MODEL=model)
    return {key: value for key, value in env.items() if not key.upper().endswith("_GOLD")}


def command(cfg: Config, name: str, *argv: str, kind="command", ok_codes=(0,),
            env=None, cwd=None) -> Step:
    if kind == "ai":
        ok_codes = AI_OK_CODES
    return Step(name, tuple(argv), ok_codes, kind, child_env(cfg.model, env), cwd or cfg.root)


def python_step(cfg: Config, name: str, script: str, *args: str, **kwargs) -> Step:
    return command(cfg, name, str(cfg.root / ".venv/Scripts/python.exe"),
                   f"scripts/{script}.py", *args, **kwargs)


def round_key(bundle: int, number: int) -> str:
    if bundle not in range(1, 7) or number not in ROUND_ORDER:
        raise ValueError("bundle must be 1..6 and round must be 1 or 3")
    return f"2026-round-{number}-nw{bundle}"


def roster_path(bundle: int, number: int) -> str:
    round_key(bundle, number)
    return f"data/rosters/middle-nw{bundle}-round-{number}.csv"


def ai_args(cfg: Config) -> tuple[str, ...]:
    return ("--isolated-cwd", str(cfg.isolated_cwd), "--workers", str(cfg.workers),
            "--model", cfg.model)


def round_steps(cfg: Config, bundle: int, number: int, *, key: str | None = None) -> list[Step]:
    key = key or round_key(bundle, number)
    if "gold" in key.casefold() or key != round_key(bundle, number):
        raise ValueError(f"invalid nationwide round key: {key}")
    roster = roster_path(bundle, number)
    collect = ("--roster", roster, "--round", str(number), "--run-label", f"nw{bundle}")
    steps = [
        python_step(cfg, "collect", "collect_schoolinfo_4ga_round", *collect, kind="collect"),
        python_step(cfg, "collect-retry", "collect_schoolinfo_4ga_round", *collect,
                    "--retry-failed", kind="collect"),
        python_step(cfg, "conversion", "audit_middle_conversion", "--round-key", key),
        python_step(cfg, "segments", "audit_middle_segments", "--round-key", key,
                    "--roster", roster, "--reuse-conversions"),
    ]
    for name in ("subjects", "items"):
        steps.append(python_step(cfg, name, f"audit_middle_{name}", "--round-key", key,
                                 "--roster", roster))
    for script, names in (
        ("middle_ai_first", ("targets", "run", "verify", "merge")),
        ("middle_ai_read", ("fields-rule", "fields-targets", "fields-run",
                            "fields-verify", "fields-merge")),
    ):
        for name in names:
            is_ai = name in ("run", "fields-run")
            label = f"first-{name}" if script == "middle_ai_first" else name
            steps.append(python_step(cfg, label, script, name, "--round-key", key,
                                     *(ai_args(cfg) if is_ai else ()),
                                     kind="ai" if is_ai else "command"))
    steps.extend([
        python_step(cfg, "first-methods", "middle_ai_first", "methods", "--round-key", key),
        python_step(cfg, "axes", "science_axes", "classify", "--items",
                    f"data/derived/items_ai/{key}.json", "--out", f"data/derived/axes/{key}.json"),
    ])
    return steps


def publication_rounds(state: dict) -> tuple[str, ...]:
    result = list(DEFAULT_ROUNDS)
    for bundle in sorted(state.get("bundles", {}), key=int):
        rounds = state["bundles"][bundle]["rounds"]
        for number in ROUND_ORDER:
            key = round_key(int(bundle), number)
            if rounds.get(key, {}).get("status") == "done" and key not in result:
                result.append(key)
    return tuple(result)


def publish_steps(cfg: Config, rounds: tuple[str, ...]) -> list[Step]:
    context = tuple(key for key in rounds if "gold" not in key.casefold()
                    and (cfg.root / f"data/derived/ai_read/{key}/first/verified.json").is_file())
    axes = "data/derived/axes_ai_run"
    cards = "data/derived/card_check3"
    steps = [
        python_step(cfg, "build0", "build_science_catalog_db", "--output", DATABASE,
                    "--replace", "--rounds", *rounds),
        python_step(cfg, "context", "activity_context", "build", "--rounds", *context),
        python_step(cfg, "ax-targets", "science_axes_ai", "targets", "--database", DATABASE,
                    "--out-dir", axes, "--rounds", *rounds,
                    "--context", "data/derived/activity_context.json", *AXES_TARGET_EXTRA),
        python_step(cfg, "ax-run", "science_axes_ai", "run", "--out-dir", axes,
                    *ai_args(cfg), kind="ai"),
        python_step(cfg, "ax-export", "science_axes_ai", "export", "--database", DATABASE,
                    "--out-dir", axes, "--axes-out", "data/derived/axes_ai"),
        python_step(cfg, "hybrid", "science_axes_hybrid", "--rounds", *rounds),
        python_step(cfg, "build", "build_science_catalog_db", "--output", DATABASE,
                    "--replace", "--rounds", *rounds,
                    "--activity-axes-dir", "data/derived/axes_hybrid"),
        python_step(cfg, "cc-targets", "science_card_check", "targets", "--database", DATABASE,
                    "--out-dir", cards),
        python_step(cfg, "cc-run", "science_card_check", "run", "--out-dir", cards,
                    *ai_args(cfg), kind="ai"),
        python_step(cfg, "cc-excl", "science_card_check", "exclusions", "--database", DATABASE,
                    "--out-dir", cards, "--out", f"{cards}/card-exclusions.csv"),
        python_step(cfg, "audit-full", "run_science_audits", "--database", DATABASE,
                    "--out-dir", "data/derived/science_audit", ok_codes=(0, 1)),
        python_step(cfg, "exclusions", "apply_science_publication_exclusions", "--source", DATABASE,
                    "--risk-queue", "data/derived/science_audit/risk-queue.csv",
                    "--risk-queue", f"{cards}/card-exclusions.csv", "--output", PUBLIC_DATABASE,
                    "--report", "data/derived/science_audit/publication-exclusions.json"),
        python_step(cfg, "audit-public", "run_science_audits", "--database", PUBLIC_DATABASE,
                    "--out-dir", "data/derived/science_audit_public", "--card-verified",
                    f"{cards}/verified.json", env={"MATH_ASSESSMENT_DETAIL_DB": PUBLIC_DATABASE}),
        python_step(cfg, "method-text", "check_science_method_text", "--database", PUBLIC_DATABASE,
                    "--output", "json", ok_codes=(0, 1)),
    ]
    return steps


def gate_steps(cfg: Config) -> list[Step]:
    env = {"MATH_ASSESSMENT_DETAIL_DB": str((cfg.root / PUBLIC_DATABASE).resolve())}
    return [
        command(cfg, "renderer", "npm", "run", "audit:renderer", kind="renderer", env=env),
        python_step(cfg, "registry", "build_science_source_registry", "--database", PUBLIC_DATABASE,
                    "--out", "data/publish/official_math_source_registry.json"),
        command(cfg, "package", "npm", "run", "package:vercel"),
    ]
