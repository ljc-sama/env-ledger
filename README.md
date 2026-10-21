# env-ledger

下载文件，顺手记一笔，日后能验。

装软件、配环境时，经常从各种站点下载安装包。过几个月回头想：这东西哪来的？是不是被人换过？
`env-ledger` 的做法很简单——**每下载一个文件，就把来源、大小、SHA256 记进一张 CSV**，
之后随时可以一键校验，看文件有没有被改动或删除。

只用 Python 标准库，没有任何第三方依赖。

## 安装

```bash
pip install .
```

想边改边用：

```bash
pip install -e .
```

## 用法

### 下载并记账

```bash
env-ledger fetch https://example.com/tool-1.2.3.zip -p "装某某工具" -v 1.2.3
```

```
已下载 tool-1.2.3.zip  4.21 MB
SHA256 9F2C1A...E4B7
保存到 /home/user/Downloads/env-ledger/2026-10-21/tool-1.2.3.zip
已记账 -> /home/user/env-ledger/ledger.csv
```

`-p/--purpose` 是必填的，它强制你想清楚**为什么要下这个文件**。
半年后回来看这一行，你会庆幸当时写了。

### 查看记录

```bash
env-ledger list
```

```
TIME              FILE                VERSION  MB    STATUS
----------------  ------------------  -------  ----  ----------
2026-10-21 12:12  tool-1.2.3.zip      1.2.3    4.21  downloaded
2026-10-21 12:20  python-3.13.16.exe  3.13.16  28.52 downloaded
```

### 校验文件

```bash
env-ledger verify
```

```
[OK      ] tool-1.2.3.zip  /home/user/Downloads/.../tool-1.2.3.zip
[MISSING ] python-3.13.16.exe  /home/user/Downloads/.../python-3.13.16.exe

1 个文件有问题，1 个正常。
```

三种状态：

| 标记 | 含义 |
|---|---|
| `OK` | 文件在，哈希对得上 |
| `MISSING` | 记录里有，文件没了 |
| `TAMPERED` | 文件在，但内容和当初下载的不一致 |

有问题时退出码为 `1`，可以直接塞进脚本或 CI 里做检查。

### 换账本位置

```bash
env-ledger --ledger D:\notes\downloads.csv list
```

默认账本是 `~/env-ledger/ledger.csv`。

## 它怎么工作

```
fetch  →  下载到 <目录>/<日期>/  →  算 SHA256  →  追加一行 CSV
verify →  读 CSV  →  逐个比对哈希  →  报告 OK / MISSING / TAMPERED
```

几个刻意的设计：

- **原子写**：账本先写临时文件再整体替换，中途断电不会写坏半个 CSV。
- **流式哈希**：按 1 MiB 分块读取，几个 GB 的文件也不会吃爆内存。
- **CSV 而不是数据库**：可以用 Excel 打开，可以 `git diff`，可以手工编辑。
- **零依赖**：只有标准库，随便扔到哪台机器都能跑。

账本列结构：

| 列 | 含义 |
|---|---|
| `time` | 下载时间 |
| `file` | 文件名 |
| `version` | 版本号（可选） |
| `purpose` | 下载目的 |
| `url` | 来源地址 |
| `size_mb` | 大小 |
| `sha256` | 文件指纹 |
| `path` | 本地完整路径 |
| `status` | 状态 |

## 测试

```bash
python -m unittest discover -s tests -v
```

测试全部用 `file://` 造假下载，**不联网**也能跑。CI 在 Ubuntu 上覆盖 Python 3.9 ~ 3.13。

## 来历

这个项目是 2026 年 10 月 21 日，由 **大肥鱼** 在 DeepSeek Harness 里写出来的。

起因很具体：那台 Windows 机器上装 Git 和 Python，下载完安装包之后，
突然想到「以后要是想不起来这些包哪来的、有没有被动过怎么办」。
于是先手写了个 PowerShell 脚本记账，再整理成这个跨平台的小工具。

代码由 AI 编写，测试通过，第一次提交就带 CI。
如果有人要拿去用，随便用，MIT 协议。

## 协议

[MIT](LICENSE)
