"""Central filesystem configuration for ASTRA scripts (ADR-0065).

Every script resolves its data, model and output locations through ``get_paths()``
instead of hard-coding them. Each location has a repository-relative default and can be
overridden with an environment variable; relative override values are resolved against
the repository root, so ``ASTRA_PROCESSED_DIR=astra-platform/data/processed`` works from
any working directory.

| Path               | Environment variable      | Default                         |
|--------------------|---------------------------|---------------------------------|
| phase6_root        | ASTRA_PHASE6_ROOT         | data/phase6                     |
| processed_dir      | ASTRA_PROCESSED_DIR       | <phase6_root>/processed         |
| splits_dir         | ASTRA_SPLITS_DIR          | <phase6_root>/splits            |
| models_dir         | ASTRA_MODELS_DIR          | models/saved                    |
| output_dir         | ASTRA_OUTPUT_DIR          | outputs (git-ignored)           |
| lightkurve_cache   | ASTRA_LIGHTKURVE_CACHE    | ~/.lightkurve/cache             |
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_PHASE6_ROOT = "ASTRA_PHASE6_ROOT"
ENV_PROCESSED_DIR = "ASTRA_PROCESSED_DIR"
ENV_SPLITS_DIR = "ASTRA_SPLITS_DIR"
ENV_MODELS_DIR = "ASTRA_MODELS_DIR"
ENV_OUTPUT_DIR = "ASTRA_OUTPUT_DIR"
ENV_LIGHTKURVE_CACHE = "ASTRA_LIGHTKURVE_CACHE"


@dataclass(frozen=True)
class AstraPaths:
    project_root: Path
    phase6_root: Path
    processed_dir: Path
    splits_dir: Path
    models_dir: Path
    output_dir: Path
    lightkurve_cache: Path

    def output(self, *parts: str) -> Path:
        """Return a path under ``output_dir``, creating its parent directory."""
        path = self.output_dir.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def model(self, filename: str) -> Path:
        """Return the path of a file in ``models_dir``."""
        return self.models_dir / filename


def _resolve(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path)


def resolve_cli_path(value: str | Path | None, default: Path, project_root: Path | None = None) -> Path:
    """Resolve a command-line path argument.

    ``None`` (argument not given) returns ``default``. Relative values are resolved
    against the repository root, matching the environment-variable overrides, so a
    command works the same from any working directory.
    """
    if value is None or str(value) == "":
        return default
    return _resolve(str(value), (project_root or PROJECT_ROOT).resolve())


def get_paths(env: Mapping[str, str] | None = None, project_root: Path | None = None) -> AstraPaths:
    """Resolve all ASTRA paths from ``env`` (default: ``os.environ``)."""
    env = os.environ if env is None else env
    root = (project_root or PROJECT_ROOT).resolve()

    def pick(name: str, default: Path) -> Path:
        value = env.get(name)
        return _resolve(value, root) if value else default

    phase6_root = pick(ENV_PHASE6_ROOT, root / "data" / "phase6")
    return AstraPaths(
        project_root=root,
        phase6_root=phase6_root,
        processed_dir=pick(ENV_PROCESSED_DIR, phase6_root / "processed"),
        splits_dir=pick(ENV_SPLITS_DIR, phase6_root / "splits"),
        models_dir=pick(ENV_MODELS_DIR, root / "models" / "saved"),
        output_dir=pick(ENV_OUTPUT_DIR, root / "outputs"),
        lightkurve_cache=pick(ENV_LIGHTKURVE_CACHE, Path.home() / ".lightkurve" / "cache"),
    )
