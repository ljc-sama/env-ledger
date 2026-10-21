"""env-ledger: 下载文件并留下可校验的账本。

核心只有三件事：
1. 下载一个 URL 到本地目录
2. 算 SHA256 并追加一行记录到 CSV
3. 之后随时可以按记录校验文件有没有被动过

只用标准库，没有第三方依赖。
"""

from __future__ import annotations

import csv
import hashlib
import os
import tempfile
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List

COLUMNS = [
    "time",
    "file",
    "version",
    "purpose",
    "url",
    "size_mb",
    "sha256",
    "path",
    "status",
]

CHUNK_SIZE = 1 << 20  # 1 MiB


@dataclass
class Entry:
    """账本里的一行。"""

    time: str
    file: str
    version: str
    purpose: str
    url: str
    size_mb: str
    sha256: str
    path: str
    status: str


@dataclass
class VerifyResult:
    """校验结果：ok / missing / mismatch。"""

    entry: Entry
    state: str


def sha256_of(path: Path) -> str:
    """流式计算文件的 SHA256，大文件不会一次性读进内存。"""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_ledger(ledger_path: Path) -> List[Entry]:
    """读取账本，文件不存在就当作空账本。"""
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return []
    with ledger_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [
            Entry(**{key: (row.get(key) or "") for key in COLUMNS})
            for row in csv.DictReader(fh)
        ]


def write_ledger(ledger_path: Path, entries: List[Entry]) -> None:
    """原子写入：先写临时文件再替换，避免中途失败把账本写坏。"""
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(ledger_path.parent), suffix=".tmp")
    os.close(fd)
    try:
        with open(tmp_name, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            for entry in entries:
                writer.writerow(asdict(entry))
        os.replace(tmp_name, ledger_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def append_entry(ledger_path: Path, entry: Entry) -> None:
    entries = read_ledger(ledger_path)
    entries.append(entry)
    write_ledger(ledger_path, entries)


def download(url: str, target: Path, timeout: float = 60.0) -> int:
    """把 url 下载到 target，返回字节数。支持 http(s) 和 file://。"""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "env-ledger/0.1"})
    written = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with target.open("wb") as out:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                out.write(chunk)
                written += len(chunk)
    return written


def filename_from_url(url: str) -> str:
    name = Path(urllib.parse.urlparse(url).path).name
    return name or "download.bin"


def fetch(
    url: str,
    ledger_path: Path,
    purpose: str,
    version: str = "",
    out_dir: Path | None = None,
    timeout: float = 60.0,
) -> Entry:
    """下载并记账。"""
    name = filename_from_url(url)
    if out_dir is None:
        out_dir = Path.home() / "Downloads" / "env-ledger" / datetime.now().strftime("%Y-%m-%d")
    target = Path(out_dir) / name

    size = download(url, target, timeout=timeout)

    entry = Entry(
        time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        file=name,
        version=version,
        purpose=purpose,
        url=url,
        size_mb=f"{size / 1048576:.2f}",
        sha256=sha256_of(target),
        path=str(target),
        status="downloaded",
    )
    append_entry(ledger_path, entry)
    return entry


def verify_ledger(ledger_path: Path) -> List[VerifyResult]:
    """逐条校验：文件还在吗？哈希还对吗？"""
    results: List[VerifyResult] = []
    for entry in read_ledger(ledger_path):
        path = Path(entry.path)
        if not path.exists():
            results.append(VerifyResult(entry, "missing"))
        elif sha256_of(path) != entry.sha256.upper():
            results.append(VerifyResult(entry, "mismatch"))
        else:
            results.append(VerifyResult(entry, "ok"))
    return results
