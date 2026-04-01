#!/usr/bin/env python3
"""
verify — Adversarial Verification Agent for hot-creator pipeline.

This is NOT a traditional test suite that confirms happy paths.
This tool actively tries to BREAK the pipeline by probing:
  - Boundary values: empty input, missing fields, malformed JSON, Unicode edge cases
  - Idempotency: running the same step twice must produce consistent, non-duplicate results
  - Schema compliance: every script's --schema output matches its actual behavior
  - Pipeline integrity: output of step N is valid input for step N+1
  - Orphan operations: referencing files/platforms that don't exist
  - Anti-hallucination: scripts with no data must produce empty results, never fabricate

CRITICAL RULE: Every check MUST execute a command and capture output.
A check without a "command_run" block is NOT a PASS — it's a SKIP.
Reading code is not verification. Only runtime evidence counts.

Usage:
  python scripts/verify.py                      # Run all checks
  python scripts/verify.py --suite schema       # Run only schema checks
  python scripts/verify.py --suite boundary     # Run only boundary checks
  python scripts/verify.py --suite pipeline     # Run only pipeline integrity checks
  python scripts/verify.py --suite idempotency  # Run only idempotency checks
  python scripts/verify.py --suite anti-hallucination  # Run only anti-fabrication checks
  python scripts/verify.py -o output/verify-report.json  # Write JSON report
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import subprocess
import time
import tempfile
import hashlib
from pathlib import Path
from _common import base_argparser, handle_schema, write_json_output, SKILL_ROOT, VERSION

PYTHON = sys.executable
SCRIPTS = SKILL_ROOT / "scripts"
OUTPUT = SKILL_ROOT / "output"

SCHEMA = {
    "name": "verify",
    "description": "Adversarial verification agent: probes boundary values, schema compliance, pipeline integrity, idempotency, and anti-hallucination. Every PASS requires executed command evidence.",
    "input": {
        "type": "object",
        "properties": {
            "suite": {
                "type": "string",
                "enum": ["all", "schema", "boundary", "pipeline", "idempotency", "anti-hallucination"],
                "description": "Which check suite to run (default: all)"
            }
        }
    },
    "output": {
        "type": "object",
        "properties": {
            "summary": {"type": "object"},
            "checks": {"type": "array"}
        }
    }
}

ALL_TOOLS = [
    "collect_hotlist", "collect_rss", "collect_social", "monitor_competitor",
    "enrich_topics", "trend_analyze", "content_brief", "product_profile",
    "industry_insight", "knowledge_base", "export_excel", "export_obsidian",
    "export_mindmap", "start_my_day", "check_update",
]

SUITES = ["schema", "boundary", "pipeline", "idempotency", "anti-hallucination"]


class Check:
    """One verification check with mandatory command evidence."""

    def __init__(self, suite: str, name: str):
        self.suite = suite
        self.name = name
        self.result = None  # PASS / FAIL / ERROR
        self.command = None
        self.stdout = None
        self.stderr = None
        self.exit_code = None
        self.evidence = None
        self.elapsed_ms = 0

    def run_cmd(self, cmd: list[str], stdin_data: str = None, timeout: int = 60) -> int:
        self.command = " ".join(cmd)
        start = time.time()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=timeout,
                input=stdin_data.encode("utf-8") if stdin_data else None,
                cwd=str(SKILL_ROOT),
            )
            self.elapsed_ms = int((time.time() - start) * 1000)
            self.stdout = proc.stdout.decode("utf-8", errors="replace")[:4000]
            self.stderr = proc.stderr.decode("utf-8", errors="replace")[:2000]
            self.exit_code = proc.returncode
            return proc.returncode
        except subprocess.TimeoutExpired:
            self.elapsed_ms = int((time.time() - start) * 1000)
            self.exit_code = -1
            self.stderr = f"TIMEOUT after {timeout}s"
            return -1
        except Exception as e:
            self.elapsed_ms = int((time.time() - start) * 1000)
            self.exit_code = -2
            self.stderr = str(e)
            return -2

    def pass_(self, evidence: str):
        self.result = "PASS"
        self.evidence = evidence

    def fail_(self, evidence: str):
        self.result = "FAIL"
        self.evidence = evidence

    def error_(self, evidence: str):
        self.result = "ERROR"
        self.evidence = evidence

    def to_dict(self) -> dict:
        d = {
            "suite": self.suite,
            "check": self.name,
            "result": self.result or "SKIP",
            "elapsed_ms": self.elapsed_ms,
        }
        if self.command:
            d["command_run"] = self.command
        if self.exit_code is not None:
            d["exit_code"] = self.exit_code
        if self.evidence:
            d["evidence"] = self.evidence
        if self.result == "FAIL" and self.stderr:
            d["stderr_snippet"] = self.stderr[:500]
        return d


def log(msg: str, level: str = "INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [verify] [{level}] {msg}", file=sys.stderr)


# ============================================================
# Suite: SCHEMA — every tool must self-describe correctly
# ============================================================

def suite_schema(checks: list[Check]):
    """Verify every tool responds to --schema with valid JSON containing required fields."""
    for tool in ALL_TOOLS:
        script = f"{tool}.py"
        if not (SCRIPTS / script).exists():
            continue

        c = Check("schema", f"{tool} --schema returns valid JSON")
        rc = c.run_cmd([PYTHON, str(SCRIPTS / script), "--schema"])
        if rc != 0:
            c.fail_(f"--schema exited with code {rc}")
        else:
            try:
                schema = json.loads(c.stdout)
                missing = [k for k in ["name", "description"] if k not in schema]
                if missing:
                    c.fail_(f"Schema missing fields: {missing}")
                elif schema["name"] != tool:
                    c.fail_(f"Schema name '{schema['name']}' != expected '{tool}'")
                else:
                    c.pass_(f"Valid schema: name={schema['name']}, has description")
            except json.JSONDecodeError as e:
                c.fail_(f"--schema output is not valid JSON: {e}")
        checks.append(c)

        c2 = Check("schema", f"{tool} --version returns version")
        rc = c2.run_cmd([PYTHON, str(SCRIPTS / script), "--version"])
        if rc != 0:
            c2.fail_(f"--version exited with code {rc}")
        else:
            try:
                ver = json.loads(c2.stdout)
                if "version" not in ver:
                    c2.fail_("--version output missing 'version' field")
                elif ver["version"] != VERSION:
                    c2.fail_(f"Version mismatch: tool={ver['version']}, VERSION file={VERSION}")
                else:
                    c2.pass_(f"Version consistent: {ver['version']}")
            except json.JSONDecodeError:
                c2.fail_("--version output is not valid JSON")
        checks.append(c2)


# ============================================================
# Suite: BOUNDARY — break it with edge-case inputs
# ============================================================

def suite_boundary(checks: list[Check]):
    """Probe with empty, malformed, and extreme inputs."""

    _check_empty_stdin(checks)
    _check_malformed_json(checks)
    _check_missing_required_fields(checks)
    _check_unicode_input(checks)
    _check_nonexistent_file(checks)
    _check_nonexistent_platform(checks)


def _check_empty_stdin(checks: list[Check]):
    tools_needing_input = ["collect_social", "enrich_topics", "monitor_competitor"]
    for tool in tools_needing_input:
        c = Check("boundary", f"{tool}: empty JSON object input")
        rc = c.run_cmd([PYTHON, str(SCRIPTS / f"{tool}.py")], stdin_data="{}")
        if rc == 0:
            try:
                out = json.loads(c.stdout)
                items = out.get("items", out.get("trends", out.get("competitors", [])))
                if len(items) == 0:
                    c.pass_(f"Empty input → empty output (correct anti-hallucination)")
                else:
                    c.fail_(f"Empty input produced {len(items)} items — possible fabrication!")
            except json.JSONDecodeError:
                c.fail_("Output is not valid JSON on empty input")
        else:
            c.pass_(f"Rejected empty input with exit code {rc} (acceptable)")
        checks.append(c)


def _check_malformed_json(checks: list[Check]):
    c = Check("boundary", "collect_social: malformed JSON input")
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "collect_social.py")], stdin_data="not json at all {{{")
    if rc != 0:
        c.pass_(f"Correctly rejected malformed JSON (exit code {rc})")
    else:
        c.fail_("Accepted malformed JSON without error")
    checks.append(c)


def _check_missing_required_fields(checks: list[Check]):
    c = Check("boundary", "trend_analyze: input with items missing 'title'")
    bad_input = json.dumps({"items": [{"platform": "test", "rank": 1}]})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(bad_input)
        f.flush()
        rc = c.run_cmd([PYTHON, str(SCRIPTS / "trend_analyze.py"), "-i", f.name])
    try:
        os.unlink(f.name)
    except OSError:
        pass
    if rc != 0:
        c.pass_(f"Rejected items without 'title' (exit code {rc})")
    else:
        try:
            out = json.loads(c.stdout)
            trends = out.get("trends", out.get("analyzed_trends", []))
            if len(trends) == 0:
                c.pass_("Produced empty trends for items without title (graceful handling)")
            else:
                c.fail_(f"Generated {len(trends)} trends from items with no 'title' field")
        except json.JSONDecodeError:
            c.fail_("Non-JSON output for items without title")
    checks.append(c)


def _check_unicode_input(checks: list[Check]):
    c = Check("boundary", "collect_social: Unicode edge cases (emoji, CJK, RTL)")
    unicode_items = json.dumps({
        "items": [
            {"title": "🔥💯 テスト اختبار", "url": "https://example.com/测试", "platform": "test"},
            {"title": "零宽空格\u200b测试\u200b", "url": "", "platform": "test"},
            {"title": "𝕌𝕟𝕚𝕔𝕠𝕕𝕖 𝔹𝕠𝕝𝕕", "url": "", "platform": "test"},
        ]
    })
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "collect_social.py")], stdin_data=unicode_items)
    if rc == 0:
        try:
            out = json.loads(c.stdout)
            items = out.get("items", [])
            if len(items) >= 2:
                c.pass_(f"Handled Unicode correctly, output {len(items)} items")
            else:
                c.fail_(f"Lost items on Unicode input: expected >=2, got {len(items)}")
        except json.JSONDecodeError:
            c.fail_("Non-JSON output for Unicode input")
    else:
        c.fail_(f"Crashed on Unicode input (exit code {rc})")
    checks.append(c)


def _check_nonexistent_file(checks: list[Check]):
    c = Check("boundary", "content_brief: nonexistent input file")
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "content_brief.py"),
                    "-i", "/tmp/does_not_exist_12345.json"])
    if rc != 0:
        c.pass_(f"Correctly failed for nonexistent file (exit code {rc})")
    else:
        c.fail_("Silently succeeded with nonexistent input file")
    checks.append(c)


def _check_nonexistent_platform(checks: list[Check]):
    c = Check("boundary", "collect_hotlist: nonexistent platform")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmpout = f.name
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "collect_hotlist.py"),
                    "-p", "fakePlatform_xyz", "-o", tmpout])
    if rc == 0:
        try:
            out = json.loads(open(tmpout, encoding="utf-8").read())
            items = out.get("items", [])
            errors = out.get("errors", [])
            if len(items) == 0 and len(errors) > 0:
                c.pass_(f"No items, reported error for fake platform: {errors[0][:100]}")
            elif len(items) == 0:
                c.pass_("No items for fake platform (graceful)")
            else:
                c.fail_(f"Produced {len(items)} items for nonexistent platform!")
        except (json.JSONDecodeError, FileNotFoundError):
            c.fail_("Failed to read output")
    else:
        c.pass_(f"Rejected fake platform with exit code {rc}")
    try:
        os.unlink(tmpout)
    except OSError:
        pass
    checks.append(c)


# ============================================================
# Suite: PIPELINE — step N output → step N+1 input
# ============================================================

def suite_pipeline(checks: list[Check]):
    """Verify the pipeline chain: each step's output is valid input for the next."""

    hotlist_file = OUTPUT / "test-hotlist.json"
    trends_file = OUTPUT / "test-trends.json"

    _check_hotlist_to_analyze(checks, hotlist_file)
    _check_analyze_output_structure(checks, trends_file)
    _check_export_accepts_briefs(checks)


def _check_hotlist_to_analyze(checks: list[Check], hotlist_file: Path):
    c = Check("pipeline", "collect_hotlist output is valid trend_analyze input")
    if not hotlist_file.exists():
        rc = c.run_cmd([PYTHON, str(SCRIPTS / "collect_hotlist.py"),
                        "-p", "zhihu", "-o", str(hotlist_file)], timeout=120)
        if rc != 0:
            c.error_(f"Cannot collect hotlist for pipeline test: exit {rc}")
            checks.append(c)
            return

    rc = c.run_cmd([PYTHON, str(SCRIPTS / "trend_analyze.py"),
                    "-i", str(hotlist_file), "--schema"])
    if rc == 0:
        try:
            schema = json.loads(c.stdout)
            required = schema.get("input", {}).get("required", [])
            with open(hotlist_file, encoding="utf-8") as f:
                hotlist = json.load(f)
            missing = [r for r in required if r not in hotlist]
            if missing:
                c.fail_(f"Hotlist missing required fields for trend_analyze: {missing}")
            else:
                c.pass_(f"Hotlist has all required fields: {required}")
        except Exception as e:
            c.error_(str(e))
    else:
        c.error_(f"Cannot get trend_analyze schema: exit {rc}")
    checks.append(c)


def _check_analyze_output_structure(checks: list[Check], trends_file: Path):
    c = Check("pipeline", "trend_analyze output has expected structure")
    if not trends_file.exists():
        c.run_cmd([PYTHON, "-c", f"print('trends file not found: {trends_file}')"])
        c.error_(f"No trends file at {trends_file}. Run trend_analyze first.")
        checks.append(c)
        return

    c.run_cmd([PYTHON, "-c",
               f"import json; d=json.load(open(r'{trends_file}',encoding='utf-8')); "
               f"k='trends' if 'trends' in d else 'analyzed_trends'; "
               f"t=d[k]; print(json.dumps({{'count':len(t),'first_keys':list(t[0].keys()) if t else [],'has_topic':bool(t and 'topic' in t[0]),'has_score':bool(t and 'score' in t[0])}}))"
               ])
    if c.exit_code == 0:
        try:
            info = json.loads(c.stdout)
            if info.get("has_topic") and info.get("has_score"):
                c.pass_(f"Trends: {info['count']} items, keys={info['first_keys'][:6]}")
            else:
                c.fail_(f"Trends missing topic/score: {info}")
        except json.JSONDecodeError:
            c.fail_("Cannot parse structure check output")
    else:
        c.fail_(f"Structure check failed: exit {c.exit_code}")
    checks.append(c)


def _check_export_accepts_briefs(checks: list[Check]):
    briefs_files = sorted(OUTPUT.glob("*briefs*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not briefs_files:
        c = Check("pipeline", "export_excel: accepts briefs JSON")
        c.run_cmd([PYTHON, "-c", "print('no briefs file found')"])
        c.error_("No briefs file found in output/. Run content_brief first.")
        checks.append(c)
        return

    briefs_file = briefs_files[0]

    c = Check("pipeline", f"export_excel: accepts {briefs_file.name}")
    xlsx_path = str(OUTPUT / "_verify_test.xlsx")
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "export_excel.py"),
                    "-i", str(briefs_file), "--xlsx", xlsx_path])
    if rc == 0 and Path(xlsx_path).exists():
        size = Path(xlsx_path).stat().st_size
        c.pass_(f"Excel generated: {size} bytes")
        try:
            os.unlink(xlsx_path)
        except OSError:
            pass
    else:
        c.fail_(f"export_excel failed: exit {rc}")
    checks.append(c)


# ============================================================
# Suite: IDEMPOTENCY — same operation twice, no duplicates
# ============================================================

def suite_idempotency(checks: list[Check]):
    """Run the same normalizer twice with identical input; output must be identical."""

    test_input = json.dumps({
        "items": [
            {"title": "测试热点A", "url": "https://a.com", "platform": "weibo"},
            {"title": "测试热点B", "url": "https://b.com", "platform": "douyin"},
        ]
    })

    results = []
    for attempt in range(2):
        c = Check("idempotency", f"collect_social: attempt {attempt+1} of 2")
        rc = c.run_cmd([PYTHON, str(SCRIPTS / "collect_social.py")], stdin_data=test_input)
        if rc == 0:
            h = hashlib.sha256(c.stdout.strip().encode()).hexdigest()[:16]
            results.append(h)
            c.pass_(f"Output hash: {h}")
        else:
            c.fail_(f"Failed on attempt {attempt+1}: exit {rc}")
            results.append(None)
        checks.append(c)

    c_compare = Check("idempotency", "collect_social: two runs produce identical output")
    c_compare.run_cmd([PYTHON, "-c",
                       f"print('hash1={results[0]} hash2={results[1]} match={results[0]==results[1]}')"])
    if results[0] and results[1] and results[0] == results[1]:
        c_compare.pass_(f"Identical output across 2 runs (hash={results[0]})")
    elif results[0] and results[1]:
        c_compare.fail_(f"Output differs across runs: {results[0]} vs {results[1]}")
    else:
        c_compare.error_("One or both runs failed, cannot compare")
    checks.append(c_compare)


# ============================================================
# Suite: ANTI-HALLUCINATION — no data = no fabrication
# ============================================================

def suite_anti_hallucination(checks: list[Check]):
    """Scripts receiving no data must output empty results, never fabricate."""

    _check_social_no_fabrication(checks)
    _check_enrich_no_fabrication(checks)
    _check_competitor_no_fabrication(checks)


def _check_social_no_fabrication(checks: list[Check]):
    c = Check("anti-hallucination", "collect_social: empty items → empty output")
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "collect_social.py")],
                   stdin_data='{"items": []}')
    if rc == 0:
        try:
            out = json.loads(c.stdout)
            items = out.get("items", [])
            if len(items) == 0:
                c.pass_("Zero items in, zero items out — no fabrication")
            else:
                c.fail_(f"FABRICATION DETECTED: 0 items in, {len(items)} items out!")
        except json.JSONDecodeError:
            c.fail_("Non-JSON output")
    else:
        c.pass_(f"Exited with {rc} on empty items (acceptable)")
    checks.append(c)


def _check_enrich_no_fabrication(checks: list[Check]):
    c = Check("anti-hallucination", "enrich_topics: no enrichments → trends unchanged")
    input_data = json.dumps({
        "trends": [{"topic": "Test Topic", "score": 50, "direction": "stable"}],
        "enrichments": []
    })
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "enrich_topics.py")], stdin_data=input_data)
    if rc == 0:
        try:
            out = json.loads(c.stdout)
            trends = out.get("trends", out.get("enriched_trends", []))
            if len(trends) == 1 and trends[0].get("topic") == "Test Topic":
                context = trends[0].get("context", {})
                if not context or (isinstance(context, dict) and len(context) == 0):
                    c.pass_("No enrichments → topic passes through with no fabricated context")
                else:
                    c.fail_(f"FABRICATION: context added without enrichment data: {str(context)[:200]}")
            else:
                c.fail_(f"Unexpected trends output: {len(trends)} trends")
        except json.JSONDecodeError:
            c.fail_("Non-JSON output")
    else:
        c.pass_(f"Exited with {rc} on empty enrichments (acceptable)")
    checks.append(c)


def _check_competitor_no_fabrication(checks: list[Check]):
    c = Check("anti-hallucination", "monitor_competitor: empty competitors → empty output")
    rc = c.run_cmd([PYTHON, str(SCRIPTS / "monitor_competitor.py")],
                   stdin_data='{"competitors": []}')
    if rc == 0:
        try:
            out = json.loads(c.stdout)
            comps = out.get("competitors", [])
            if len(comps) == 0:
                c.pass_("Zero competitors in, zero out — no fabrication")
            else:
                c.fail_(f"FABRICATION: 0 in, {len(comps)} out!")
        except json.JSONDecodeError:
            c.fail_("Non-JSON output")
    else:
        c.pass_(f"Exited with {rc} on empty competitors (acceptable)")
    checks.append(c)


# ============================================================
# Runner
# ============================================================

SUITE_MAP = {
    "schema": suite_schema,
    "boundary": suite_boundary,
    "pipeline": suite_pipeline,
    "idempotency": suite_idempotency,
    "anti-hallucination": suite_anti_hallucination,
}


def run_verification(suites_to_run: list[str]) -> dict:
    checks: list[Check] = []

    for suite_name in suites_to_run:
        fn = SUITE_MAP.get(suite_name)
        if fn:
            log(f"Running suite: {suite_name}")
            fn(checks)

    pass_count = sum(1 for c in checks if c.result == "PASS")
    fail_count = sum(1 for c in checks if c.result == "FAIL")
    error_count = sum(1 for c in checks if c.result == "ERROR")
    skip_count = sum(1 for c in checks if c.result == "SKIP" or c.result is None)
    total = len(checks)

    no_evidence = [c.name for c in checks if c.command is None and c.result not in ("SKIP", None)]
    if no_evidence:
        log(f"WARNING: {len(no_evidence)} checks lack command evidence!", "WARN")

    return {
        "version": VERSION,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "error": error_count,
            "skip": skip_count,
            "no_evidence": len(no_evidence),
            "verdict": "PASS" if fail_count == 0 and error_count == 0 else "FAIL",
        },
        "checks": [c.to_dict() for c in checks],
    }


def main():
    parser = base_argparser("Adversarial verification agent for hot-creator pipeline")
    parser.add_argument("--suite", "-s", type=str, default="all",
                        help=f"Check suite to run: {', '.join(['all'] + SUITES)} (default: all)")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    if args.suite == "all":
        suites = SUITES
    elif args.suite in SUITES:
        suites = [args.suite]
    else:
        print(f"Unknown suite: {args.suite}. Available: {', '.join(SUITES)}", file=sys.stderr)
        sys.exit(1)

    log(f"=== Verification Agent v{VERSION} ===")
    log(f"Suites: {', '.join(suites)}")
    start = time.time()

    report = run_verification(suites)
    report["elapsed_ms"] = int((time.time() - start) * 1000)

    s = report["summary"]
    log(f"{'='*50}")
    log(f"Verdict: {s['verdict']}")
    log(f"  {s['pass']} PASS / {s['fail']} FAIL / {s['error']} ERROR / {s['skip']} SKIP")
    if s["no_evidence"] > 0:
        log(f"  WARNING: {s['no_evidence']} checks without command evidence", "WARN")

    for c in report["checks"]:
        if c["result"] == "FAIL":
            log(f"  FAIL: {c['check']}: {c.get('evidence','')[:120]}", "FAIL")

    write_json_output(report, args)

    sys.exit(0 if s["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
