"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import ledger


def default_ledger_path() -> Path:
    return Path.home() / "env-ledger" / "ledger.csv"


def _configure_stdio() -> None:
    """Windows 下输出被重定向时，强制 UTF-8，避免中文变乱码。

    直接接在终端上时不干预：Python 3.6+ 会走控制台 API，本来就正确。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.isatty():
                continue
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def _print_table(rows, headers) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))


def cmd_fetch(args) -> int:
    entry = ledger.fetch(
        url=args.url,
        ledger_path=args.ledger,
        purpose=args.purpose,
        version=args.version,
        out_dir=args.dir,
        timeout=args.timeout,
    )
    print(f"已下载 {entry.file}  {entry.size_mb} MB")
    print(f"SHA256 {entry.sha256}")
    print(f"保存到 {entry.path}")
    print(f"已记账 -> {args.ledger}")
    return 0


def cmd_list(args) -> int:
    entries = ledger.read_ledger(args.ledger)
    if not entries:
        print("账本是空的。")
        return 0
    rows = [(e.time, e.file, e.version, e.size_mb, e.status) for e in entries]
    _print_table(rows, ["TIME", "FILE", "VERSION", "MB", "STATUS"])
    return 0


def cmd_verify(args) -> int:
    results = ledger.verify_ledger(args.ledger)
    if not results:
        print("账本是空的，没有可校验的记录。")
        return 0

    bad = 0
    for result in results:
        mark = {"ok": "OK", "missing": "MISSING", "mismatch": "TAMPERED"}[result.state]
        if result.state != "ok":
            bad += 1
        print(f"[{mark:8}] {result.entry.file}  {result.entry.path}")

    print()
    if bad:
        print(f"{bad} 个文件有问题，{len(results) - bad} 个正常。")
        return 1
    print(f"全部 {len(results)} 个文件校验通过。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="env-ledger",
        description="下载文件并留下可校验的账本。",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=default_ledger_path(),
        help="账本 CSV 路径（默认 ~/env-ledger/ledger.csv）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="下载文件并记账")
    fetch.add_argument("url", help="下载地址，支持 http(s) 和 file://")
    fetch.add_argument("-p", "--purpose", required=True, help="为什么要这个文件")
    fetch.add_argument("-v", "--version", default="", help="版本号，可留空")
    fetch.add_argument("-d", "--dir", type=Path, default=None, help="保存目录")
    fetch.add_argument("--timeout", type=float, default=60.0, help="超时秒数")
    fetch.set_defaults(func=cmd_fetch)

    listing = sub.add_parser("list", help="列出所有记录")
    listing.set_defaults(func=cmd_list)

    verify = sub.add_parser("verify", help="按记录校验文件")
    verify.set_defaults(func=cmd_verify)

    return parser


def main(argv=None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except OSError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
