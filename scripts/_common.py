"""
hot-creator shared utilities.
JSON I/O, time helpers, platform mapping, error handling, CLI framework.
"""

import sys
import json
import argparse
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _read_version_file() -> str:
    vf = Path(__file__).resolve().parent.parent / "VERSION"
    if vf.exists():
        line = vf.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if line and len(line) < 64:
            return line
    return "0.0.0"


VERSION = _read_version_file()
SKILL_ROOT = Path(__file__).resolve().parent.parent

# --- Platform registry ---
# type: "hotlist" = 热门榜单（积累热度）, "realtime" = 实时新闻流（刚发生的）

PLATFORMS = {
    # ── 热门榜单 (hotlist) ──
    "weibo":               {"name": "微博",         "type": "hotlist",  "column": "china"},
    "douyin":              {"name": "抖音",         "type": "hotlist",  "column": "china"},
    "zhihu":               {"name": "知乎",         "type": "hotlist",  "column": "china"},
    "baidu":               {"name": "百度热搜",     "type": "hotlist",  "column": "china"},
    "toutiao":             {"name": "今日头条",     "type": "hotlist",  "column": "china"},
    "bilibili-hot-search": {"name": "B站",         "type": "hotlist",  "column": "china"},
    "thepaper":            {"name": "澎湃新闻",    "type": "hotlist",  "column": "china"},
    "hupu":                {"name": "虎扑",         "type": "hotlist",  "column": "china"},
    "tieba":               {"name": "百度贴吧",     "type": "hotlist",  "column": "china"},
    "coolapk":             {"name": "酷安",         "type": "hotlist",  "column": "tech"},
    "douban":              {"name": "豆瓣",         "type": "hotlist",  "column": "china"},
    "ifeng":               {"name": "凤凰网",       "type": "hotlist",  "column": "china"},
    "nowcoder":            {"name": "牛客",         "type": "hotlist",  "column": "china"},
    "tencent-hot":         {"name": "腾讯新闻",     "type": "hotlist",  "column": "china"},
    "freebuf":             {"name": "Freebuf",      "type": "hotlist",  "column": "tech"},
    "qqvideo-tv-hotsearch":{"name": "腾讯视频",     "type": "hotlist",  "column": "china"},
    "iqiyi-hot-ranklist":  {"name": "爱奇艺",       "type": "hotlist",  "column": "china"},
    "chongbuluo-hot":      {"name": "虫部落",       "type": "hotlist",  "column": "china"},
    "36kr-renqi":          {"name": "36氪人气榜",   "type": "hotlist",  "column": "tech"},
    "wallstreetcn-hot":    {"name": "华尔街见闻",   "type": "hotlist",  "column": "finance"},
    "cls-hot":             {"name": "财联社热门",   "type": "hotlist",  "column": "finance"},
    "xueqiu-hotstock":     {"name": "雪球",         "type": "hotlist",  "column": "finance"},
    "hackernews":          {"name": "Hacker News",  "type": "hotlist",  "column": "tech"},
    "producthunt":         {"name": "Product Hunt", "type": "hotlist",  "column": "tech"},
    "github-trending-today":{"name": "GitHub",      "type": "hotlist",  "column": "tech"},
    "sspai":               {"name": "少数派",       "type": "hotlist",  "column": "tech"},
    "juejin":              {"name": "稀土掘金",     "type": "hotlist",  "column": "tech"},
    "steam":               {"name": "Steam",        "type": "hotlist",  "column": "world"},
    # ── 实时新闻流 (realtime) ──
    "zaobao":              {"name": "联合早报",     "type": "realtime", "column": "world"},
    "wallstreetcn-quick":  {"name": "华尔街见闻快讯","type": "realtime", "column": "finance"},
    "36kr-quick":          {"name": "36氪快讯",     "type": "realtime", "column": "tech"},
    "cls-telegraph":       {"name": "财联社电报",   "type": "realtime", "column": "finance"},
    "ithome":              {"name": "IT之家",       "type": "realtime", "column": "tech"},
    "gelonghui":           {"name": "格隆汇",       "type": "realtime", "column": "finance"},
    "jin10":               {"name": "金十数据",     "type": "realtime", "column": "finance"},
    "fastbull-express":    {"name": "法布财经快讯", "type": "realtime", "column": "finance"},
}

NEWSNOW_API = "https://newsnow.busiyi.world/api/s"
OUTPUT_DIR = SKILL_ROOT / "output"


def platform_name(platform_id: str) -> str:
    entry = PLATFORMS.get(platform_id)
    return entry["name"] if entry else platform_id


# Brief.materials: human-readable category names
MATERIAL_CATEGORY_LABELS = {
    "data_points": "核心数据",
    "quotes": "引用金句",
    "controversies": "争议话题",
    "emotion_triggers": "情绪触点",
    "knowledge_gems": "知识增量",
    "media_hooks": "镜头 / 画面素材",
    "screenshot_lines": "封面与字幕条文案",
    "sound_bites": "口播短句（≤20字优先）",
    "sources": "信源与报道",
    "b_roll": "B-roll 建议",
}


def material_category_label(key: str) -> str:
    return MATERIAL_CATEGORY_LABELS.get(key, key.replace("_", " ").title())


def format_material_item(item) -> str:
    """One atomic fact/quote/hook; supports dict with fact/source/how_to_use."""
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        fact = (
            item.get("fact")
            or item.get("content")
            or item.get("text")
            or item.get("line")
            or item.get("title")
            or ""
        )
        takeaway = item.get("takeaway") or item.get("摘要") or ""
        if not fact and takeaway:
            fact = takeaway
        source = item.get("source") or item.get("出处") or ""
        url = item.get("url") or ""
        use = item.get("how_to_use") or item.get("usage") or item.get("用于") or ""
        platform = item.get("platform") or item.get("适合平台") or ""
        bits = []
        if fact:
            bits.append(str(fact).strip())
        if url:
            bits.append(f"链接 {url}")
        elif source and str(source) not in str(fact):
            bits.append(f"来源 {source}")
        if platform:
            bits.append(f"适合 {platform}")
        if use:
            bits.append(f"用法 {use.strip()}")
        if bits:
            return " · ".join(bits)
        try:
            return json.dumps(item, ensure_ascii=False)
        except Exception:
            return str(item)
    return str(item).strip()


def retry_request(fn, max_retries: int = 3, backoff: float = 1.0, on_fail: str = ""):
    """Retry a callable up to max_retries times with exponential backoff."""
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                wait = backoff * (2 ** attempt)
                print(f"[retry] Attempt {attempt+1} failed: {e}. Retrying in {wait:.1f}s...",
                      file=sys.stderr)
                time.sleep(wait)
    if on_fail:
        print(f"[retry] All {max_retries} attempts failed: {on_fail}", file=sys.stderr)
    raise last_err


def check_deps(packages: list[str]) -> list[str]:
    """Check if packages are importable. Returns list of missing package names."""
    missing = []
    for pkg in packages:
        import_name = pkg.split(">=")[0].split("==")[0].strip()
        if import_name == "pyyaml":
            import_name = "yaml"
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    return missing


def ensure_deps(packages: list[str]):
    """Check deps and auto-install missing ones via pip."""
    missing = check_deps(packages)
    if not missing:
        return
    print(f"[deps] Missing: {', '.join(missing)}. Auto-installing...", file=sys.stderr)
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
            stdout=subprocess.DEVNULL,
        )
        print(f"[deps] Installed: {', '.join(missing)}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        fail(f"Failed to auto-install dependencies: {e}\n"
             f"Run manually: pip install {' '.join(missing)}")


def china_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def today_str() -> str:
    return china_now().strftime("%Y-%m-%d")


def default_output_path(tool_name: str, ext: str = "json") -> str:
    """Generate default output path: output/{date}-{tool}.{ext}"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return str(OUTPUT_DIR / f"{today_str()}-{tool_name}.{ext}")


# --- JSON I/O ---

def read_json_input(args) -> dict:
    """Read JSON from --input file or stdin. Non-blocking: won't hang if stdin has no data."""
    if hasattr(args, "input") and args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return json.load(f)
    if not sys.stdin.isatty():
        import select
        if sys.platform == "win32":
            import msvcrt
            if msvcrt.kbhit() or _stdin_has_data():
                return json.load(sys.stdin)
        else:
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                return json.load(sys.stdin)
    return {}


def _stdin_has_data() -> bool:
    """Windows-compatible check for whether stdin has pending data."""
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        if handle == -1:
            return False
        avail = wintypes.DWORD(0)
        result = kernel32.PeekNamedPipe(
            handle, None, 0, None, ctypes.byref(avail), None
        )
        return result != 0 and avail.value > 0
    except Exception:
        return False


def write_json_output(data: dict, args):
    """Write JSON to --output file or stdout."""
    indent = 2 if (hasattr(args, "pretty") and args.pretty) else None
    text = json.dumps(data, ensure_ascii=False, indent=indent)
    if hasattr(args, "output") and args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")


# --- CLI framework ---

def base_argparser(description: str) -> argparse.ArgumentParser:
    """Create an ArgumentParser with common flags."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", "-i", help="Input JSON file (default: stdin)")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--schema", action="store_true", help="Print tool JSON Schema and exit")
    parser.add_argument("--version", action="store_true", help="Print tool version and exit")
    return parser


def handle_schema(args, schema: dict):
    """If --schema flag is set, print schema and exit. If --version, print version."""
    if hasattr(args, "version") and args.version:
        print(json.dumps({"version": VERSION, "tool": schema.get("name", "unknown")}, ensure_ascii=False))
        sys.exit(0)
    if args.schema:
        print(json.dumps(schema, ensure_ascii=False, indent=2))
        sys.exit(0)


# --- Input validation ---

def validate_required_fields(data: dict, fields: list[str], context: str = "input") -> list[str]:
    """Check required fields exist and are non-empty. Returns list of error messages."""
    errors = []
    for field in fields:
        if field not in data:
            errors.append(f"{context}: missing required field '{field}'")
        elif data[field] is None or (isinstance(data[field], (list, dict, str)) and not data[field]):
            errors.append(f"{context}: field '{field}' is empty")
    return errors


def validate_input(data: dict, schema: dict) -> list[str]:
    """Lightweight input validation against schema. Returns list of error messages."""
    errors = []
    input_schema = schema.get("input", {})
    required = input_schema.get("required", [])
    errors.extend(validate_required_fields(data, required))

    props = input_schema.get("properties", {})
    for key, val in data.items():
        if key in props:
            expected_type = props[key].get("type")
            if expected_type == "array" and not isinstance(val, list):
                errors.append(f"'{key}' should be array, got {type(val).__name__}")
            elif expected_type == "object" and not isinstance(val, dict):
                errors.append(f"'{key}' should be object, got {type(val).__name__}")
            elif expected_type == "string" and not isinstance(val, str):
                errors.append(f"'{key}' should be string, got {type(val).__name__}")
            elif expected_type == "integer" and not isinstance(val, int):
                errors.append(f"'{key}' should be integer, got {type(val).__name__}")
    return errors


# --- Error helpers ---

def fail(message: str, code: int = 1):
    """Print structured error JSON to stderr and exit."""
    error_payload = {
        "error": message,
        "code": code,
        "hint": _error_hint(message),
    }
    print(json.dumps(error_payload, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


def structured_error(tool_name: str, error: Exception, context: str = "") -> dict:
    """Build a structured error dict for inclusion in tool output."""
    return {
        "tool": tool_name,
        "error_type": type(error).__name__,
        "message": str(error),
        "context": context,
        "traceback": traceback.format_exc().split("\n")[-3] if traceback.format_exc() else "",
    }


def _error_hint(message: str) -> str:
    """Generate actionable hint based on common error patterns."""
    msg = message.lower()
    if "feedparser" in msg:
        return "Run: pip install feedparser"
    if "openpyxl" in msg:
        return "Run: pip install openpyxl"
    if "pypdf" in msg:
        return "Run: pip install pypdf"
    if "timeout" in msg:
        return "Network timeout. Check connectivity or try a single platform first."
    return ""
