#!/usr/bin/env python3
"""
audit_error_handling.py
-----------------------
Scans all service files (app/*/services/**/*.py) and reports:

  1. HTTPException raised inside a service  ← layering violation
  2. ValueError raised inside a service     ← should be AppError
  3. Files that correctly use AppError/NotFoundError/ConflictError/ForbiddenError
  4. Files over 150 lines                   ← project hard limit

Usage:
    python audit_error_handling.py                   # expects ./app/ in cwd
    python audit_error_handling.py /path/to/backend  # explicit root
"""

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

LINE_LIMIT = 150

APP_ERROR_CLASSES = {
    "AppError", "NotFoundError", "ConflictError", "ForbiddenError",
}

# Files that are already known-good — skip noise
SKIP_FILES: set[str] = {
    "app/vat_reports/services/intake.py",
    "app/annual_reports/services/query_service.py",
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Violation:
    line: int
    kind: str        # "HTTPException" | "ValueError"
    snippet: str


@dataclass
class FileReport:
    path: str
    line_count: int
    violations: list[Violation] = field(default_factory=list)
    uses_app_error: bool = False
    over_limit: bool = False

    @property
    def clean(self) -> bool:
        return not self.violations and not self.over_limit


# ── AST visitor ───────────────────────────────────────────────────────────────

class ServiceVisitor(ast.NodeVisitor):
    """Walk an AST and collect Raise nodes that violate the rules."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.violations: list[Violation] = []
        self.uses_app_error = False

    def _name_of(self, node: ast.expr) -> str | None:
        """Return the top-level name of a Call or Name node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Call):
            return self._name_of(node.func)
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is None:
            return

        name = self._name_of(node.exc)
        lineno = node.lineno
        snippet = self.source_lines[lineno - 1].strip() if lineno <= len(self.source_lines) else ""

        if name == "HTTPException":
            self.violations.append(Violation(lineno, "HTTPException", snippet))
        elif name == "ValueError":
            self.violations.append(Violation(lineno, "ValueError", snippet))
        elif name in APP_ERROR_CLASSES:
            self.uses_app_error = True

        self.generic_visit(node)


# ── Core scan logic ───────────────────────────────────────────────────────────

def find_service_files(root: Path) -> list[Path]:
    """Return all .py files under app/*/services/ (any depth)."""
    return sorted(root.glob("app/*/services/**/*.py"))


def analyse_file(path: Path, root: Path) -> FileReport | None:
    rel = str(path.relative_to(root))

    if rel in SKIP_FILES:
        return None

    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    line_count = len(lines)

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        print(f"{RED}Syntax error in {rel}: {exc}{RESET}")
        return None

    visitor = ServiceVisitor(lines)
    visitor.visit(tree)

    return FileReport(
        path=rel,
        line_count=line_count,
        violations=visitor.violations,
        uses_app_error=visitor.uses_app_error,
        over_limit=line_count > LINE_LIMIT,
    )


# ── Report printer ────────────────────────────────────────────────────────────

def print_report(reports: list[FileReport]) -> None:
    violations_total = sum(len(r.violations) for r in reports)
    over_limit = [r for r in reports if r.over_limit]
    dirty = [r for r in reports if r.violations]
    clean = [r for r in reports if r.clean]

    print(f"\n{BOLD}{'═' * 70}{RESET}")
    print(f"{BOLD}  Error Handling Audit — Service Layer{RESET}")
    print(f"{BOLD}{'═' * 70}{RESET}\n")

    # ── Violations ────────────────────────────────────────────────────────────
    if dirty:
        print(f"{RED}{BOLD}❌ VIOLATIONS  ({len(dirty)} files, {violations_total} raises){RESET}\n")
        for report in dirty:
            http_v = [v for v in report.violations if v.kind == "HTTPException"]
            val_v  = [v for v in report.violations if v.kind == "ValueError"]
            print(f"  {BOLD}{report.path}{RESET}  ({report.line_count} lines)")
            for v in http_v:
                print(f"    {RED}L{v.line:>4}  HTTPException{RESET}  {CYAN}{v.snippet}{RESET}")
            for v in val_v:
                print(f"    {YELLOW}L{v.line:>4}  ValueError   {RESET}  {CYAN}{v.snippet}{RESET}")
            print()
    else:
        print(f"{GREEN}{BOLD}✅ No violations found.{RESET}\n")

    # ── Over limit ────────────────────────────────────────────────────────────
    if over_limit:
        print(f"{YELLOW}{BOLD}⚠️  OVER 150 LINES  ({len(over_limit)} files){RESET}\n")
        for r in over_limit:
            print(f"  {YELLOW}{r.path}{RESET}  → {r.line_count} lines")
        print()

    # ── Clean files ───────────────────────────────────────────────────────────
    if clean:
        print(f"{GREEN}✅ CLEAN  ({len(clean)} files){RESET}")
        for r in clean:
            marker = f" {GREEN}[uses AppError]{RESET}" if r.uses_app_error else ""
            print(f"  {r.path}  ({r.line_count} lines){marker}")
        print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"{BOLD}{'─' * 70}{RESET}")
    total = len(reports)
    print(
        f"  Scanned: {total} service files   "
        f"{RED}Violations: {len(dirty)}{RESET}   "
        f"{YELLOW}Over limit: {len(over_limit)}{RESET}   "
        f"{GREEN}Clean: {len(clean)}{RESET}"
    )
    print(f"{BOLD}{'─' * 70}{RESET}\n")

    if violations_total:
        print(f"{YELLOW}Run the Codex prompt to fix violations automatically.{RESET}")
        print(f"{YELLOW}Then: JWT_SECRET=test-secret pytest -q{RESET}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    if not (root / "app").is_dir():
        print(f"{RED}Error: no 'app/' directory found under {root.resolve()}{RESET}")
        print(f"Usage: python audit_error_handling.py [backend-root]")
        sys.exit(1)

    files = find_service_files(root)
    if not files:
        print(f"{YELLOW}No service files found under {root}/app/*/services/{RESET}")
        sys.exit(0)

    reports = [r for f in files if (r := analyse_file(f, root)) is not None]
    print_report(reports)

    has_violations = any(r.violations for r in reports)
    sys.exit(1 if has_violations else 0)


if __name__ == "__main__":
    main()
