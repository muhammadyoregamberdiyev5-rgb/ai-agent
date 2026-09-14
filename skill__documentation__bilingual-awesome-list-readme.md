---
name: bilingual-awesome-list-readme
description: Generate a Chinese (README_CN.md) mirror of an English awesome-list README, with mutual language-switcher badges. Covers parsing, translation mapping, and cross-file linking.
triggers:
  - "add Chinese version of README"
  - "bilingual README"
  - "中文文档"
  - "language switcher markdown"
---

# Bilingual Awesome-List README

## Overview

Produces a `README_CN.md` alongside an existing English `README.md`, with:
- Translated section headers, descriptions, TOC, overview table, footer
- Identical repo table rows (reused verbatim — no translation needed)
- Mutual language-switcher line near the top of each file

## Critical Pitfall

**`execute_code` blocks are isolated sandboxes — variables do NOT persist between calls.**  
Put the entire parse → build → write pipeline in ONE `execute_code` block, or use `terminal("cat ...")` to re-read the file at the top of each block.

## Step-by-Step

### 1. Read the EN file with `terminal("cat ...")`

Use `terminal` (not `read_file`) to get raw content without line-number prefixes:

```python
from hermes_tools import terminal, write_file
import re

r = terminal("cat '/path/to/README.md'")
en_lines = r["output"].split('\n')
```

### 2. Parse section headers → repo table rows

```python
EN_SECTION_HEADERS = {
    "## 🏛️ Official & Core": "官方与核心",
    # ... map every EN header to its ZH key
}

sections = {}   # zh_cat -> [table row strings]
current_cat = None
for line in en_lines:
    s = line.strip()
    if s in EN_SECTION_HEADERS:
        current_cat = EN_SECTION_HEADERS[s]
        sections[current_cat] = []
    elif current_cat and s.startswith('| [') and 'github.com' in s:
        sections[current_cat].append(s)
```

### 3. Define translation tables (in same block)

```python
ORDER = ["官方与核心", "精选列表与资源合集", ...]  # display order

CAT_EMOJI   = {"官方与核心": "🏛️", ...}
CAT_DESC_ZH = {"官方与核心": "Claude Code 官方仓库与 Anthropic 维护的核心资源。", ...}
```

### 4. Build CN README lines

```python
L = []

# Header block
L += [
    "# ✨ Awesome Claude Code Skills",
    "",
    "> GitHub 上 Star 数量最多的 ...",
    "",
    "[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)",
    "...",                                           # translated badges
    "",
    "**语言切换 / Language:** &nbsp; **🇨🇳 中文** &nbsp;|&nbsp; [🇺🇸 English](README.md)",
    "",
    "---",
    "",
]

# TOC
L += ["## 📋 目录", ""]
for cat in ORDER:
    emoji  = CAT_EMOJI[cat]
    count  = len(sections.get(cat, []))
    anchor = re.sub(r'[^\w\u4e00-\u9fff-]', '', cat.lower().replace(' ', '-'))
    L.append(f"- [{emoji} {cat}](#{anchor}) ({count})")
L += ["", "---", ""]

# Overview table
L += ["## 📊 概览", "", "...", "", "| 分类 | 项目数 |", "|------|:------:|"]
for cat in ORDER:
    L.append(f"| {CAT_EMOJI[cat]} {cat} | {len(sections.get(cat, []))} |")
L += ["", "---", ""]

# Sections (reuse EN table rows verbatim)
for cat in ORDER:
    rows = sections.get(cat, [])
    L += [
        f"## {CAT_EMOJI[cat]} {cat}",
        "",
        CAT_DESC_ZH[cat],
        "",
        "| 仓库 | Star | 简介 |",
        "|-----|-----:|------|",
    ]
    L += rows
    L.append("")

# Footer (Contributing + License)
L += ["---", "", "## 🤝 贡献", "", "...", "", "## 📄 许可证", "", "...", ""]
```

### 5. Write CN file

```python
write_file("/path/to/README_CN.md", '\n'.join(L))
```

### 6. Patch EN README to add language switcher

Use `patch` tool to insert one line after the badge block:

```
**Language / 语言切换:** &nbsp; **🇺🇸 English** &nbsp;|&nbsp; [🇨🇳 中文](README_CN.md)
```

## Verification

```bash
# Check row counts match
grep -c '| \[' README.md
grep -c '| \[' README_CN.md
# Both should be equal (e.g. 200)
```

## Notes

- **TOC anchors for Chinese text**: GitHub lowercases and strips non-alphanumeric/CJK chars. Use `re.sub(r'[^\w\u4e00-\u9fff-]', '', cat.lower().replace(' ', '-'))` as anchor.
- **Repo table rows**: never translate — reuse verbatim from EN so repo names/links/stars stay correct.
- **Badge URLs**: URL-encode Chinese characters or use ASCII-only badge labels to avoid rendering issues.
- **Stars badge**: keep `Combined%20Stars` in ASCII; year badge can use Chinese if URL-encoded.
