from __future__ import annotations

from pathlib import Path
import re
import subprocess


API_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

REQUIRED_INTENT_SNIPPETS = [
    "Evidence first",
    "Event comparisons are temporal comparisons",
    "`match`, `partial`, and `reject`",
    "If code needs to intentionally break one of these documented rules, ask first",
]

REQUIRED_AGENT_SNIPPETS = [
    "Intent Change Protocol",
    "Research Memory Protocol",
    "docs/project-intent.md",
    "docs/api-contract.md",
    "docs/research/decision-log.md",
    "docs/review-analysis-research-log.md",
]

REQUIRED_RESEARCH_FILES = {
    "docs/research/README.md": ["Research Memory", "User Feedback Rule"],
    "docs/research/hypotheses.md": ["Research Hypotheses", "Open"],
    "docs/research/decision-log.md": ["Research Decision Log", "Do not use pure clustering as final insight"],
    "docs/research/experiments/TEMPLATE.md": ["Question", "User Feedback", "Decision"],
    "docs/evals/review-analysis-eval.md": ["Review Analysis Evaluation", "Core Metrics"],
}

ANALYSIS_CHANGE_PATHS = {
    "backend/app/analysis.py",
    "backend/app/db.py",
    "backend/app/models.py",
    "backend/app/repository.py",
    "frontend/src/routes/+page.svelte",
}

RESEARCH_RECORD_PATHS = (
    "docs/research/",
    "docs/evals/",
    "docs/review-analysis-research-log.md",
    "docs/project-intent.md",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _api_routes(root: Path) -> list[tuple[str, str]]:
    main_py = _read(root / "backend" / "app" / "main.py")
    pattern = re.compile(r"@app\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']")
    routes = {
        (match.group(1).upper(), match.group(2))
        for match in pattern.finditer(main_py)
        if match.group(2) == "/health" or match.group(2).startswith("/api/")
    }
    return sorted(routes, key=lambda item: (item[1], item[0]))


def _documented_routes(contract_text: str) -> set[tuple[str, str]]:
    pattern = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_./{}-]+)")
    return {(match.group(1), match.group(2)) for match in pattern.finditer(contract_text)}


def _changed_paths(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()

    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:].strip().replace("\\", "/")
        if " -> " in raw_path:
            old_path, new_path = raw_path.split(" -> ", 1)
            paths.add(old_path.strip('"'))
            paths.add(new_path.strip('"'))
        else:
            paths.add(raw_path.strip('"'))
    return paths


def _has_research_record(paths: set[str]) -> bool:
    return any(path.startswith(RESEARCH_RECORD_PATHS) for path in paths)


def check_repository(root: Path | None = None) -> list[str]:
    root = root or _repo_root()
    errors: list[str] = []

    api_contract = _read(root / "docs" / "api-contract.md")
    documented_routes = _documented_routes(api_contract)
    for method, path in _api_routes(root):
        if (method, path) not in documented_routes:
            errors.append(f"Missing API contract route: {method} {path}")

    intent_text = _read(root / "docs" / "project-intent.md")
    for snippet in REQUIRED_INTENT_SNIPPETS:
        if snippet not in intent_text:
            errors.append(f"Missing project intent guardrail: {snippet}")

    agent_text = _read(root / "AGENTS.md")
    for snippet in REQUIRED_AGENT_SNIPPETS:
        if snippet not in agent_text:
            errors.append(f"Missing AGENTS.md guardrail: {snippet}")

    for relative_path, snippets in REQUIRED_RESEARCH_FILES.items():
        text = _read(root / relative_path)
        if not text:
            errors.append(f"Missing research memory file: {relative_path}")
            continue
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"Missing research memory guardrail in {relative_path}: {snippet}")

    changed_paths = _changed_paths(root)
    analysis_changes = sorted(path for path in changed_paths if path in ANALYSIS_CHANGE_PATHS)
    if analysis_changes and not _has_research_record(changed_paths):
        changed = ", ".join(analysis_changes)
        errors.append(
            "Analysis behavior changed without a research record. "
            f"Changed analysis files: {changed}. "
            "Update docs/research/, docs/evals/, docs/review-analysis-research-log.md, or docs/project-intent.md."
        )

    return errors


def main() -> int:
    errors = check_repository()
    if errors:
        print("Documentation guard failed:")
        for error in errors:
            print(f"- {error}")
        print("\nUpdate the relevant docs, or revise the code change to match the documented intent.")
        return 1
    print("Documentation guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
