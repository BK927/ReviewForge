from __future__ import annotations

from pathlib import Path
import re


API_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

REQUIRED_INTENT_SNIPPETS = [
    "Evidence first",
    "Event comparisons are temporal comparisons",
    "`match`, `partial`, and `reject`",
    "If code needs to intentionally break one of these documented rules, ask first",
]

REQUIRED_AGENT_SNIPPETS = [
    "Intent Change Protocol",
    "docs/project-intent.md",
    "docs/api-contract.md",
    "docs/review-analysis-research-log.md",
]


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
