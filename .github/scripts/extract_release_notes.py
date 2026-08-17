#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 UpdateLog.md 中提取指定 tag 版本对应的 Release Notes。

用法: python extract_release_notes.py <tag> [输出文件]
  <tag>    例如 v1.3.0（前导 v 可有可无，自动归一化）
  输出文件 默认 release_notes.md（写入当前工作目录）

提取范围: 从 `## vX.Y.Z` 标题开始，到下一个 `## vX.Y.Z` 标题（或文件末尾）之前，
包含中间的全部内容；并清理末尾的分隔线（---）与多余空行。

说明: 脚本对版本号、文件行尾均做了归一化（strip），兼容 CRLF / LF 混用，
避免 bash 环境变量带 \r 导致版本比对失败的问题。
"""
import re
import sys


def main() -> int:
    tag = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lstrip("v")
    out = (sys.argv[2] if len(sys.argv) > 2 else "release_notes.md").strip()
    if not tag:
        print("[ERROR] missing version argument, usage: extract_release_notes.py <tag>", file=sys.stderr)
        return 1

    with open("UpdateLog.md", encoding="utf-8") as fh:
        text = fh.read()

    # 所有版本标题: `## v1.3.0` / `## v1.3.0 (2026-08-17)`
    headings = list(re.finditer(r"^##\s+v?([\d.]+)", text, re.M))

    start = end = None
    for i, m in enumerate(headings):
        if m.group(1).strip() == tag:
            start = m.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            break

    if start is None:
        print(f"[WARN] version v{tag} not found in UpdateLog.md, fallback to plain version number", file=sys.stderr)
        content = f"v{tag}"
    else:
        content = text[start:end].strip()

    # 清理末尾的分隔线（---）与多余空行，正文内容保持原样
    lines = content.splitlines()
    while lines and (not lines[-1].strip() or re.fullmatch(r"-{3,}", lines[-1].strip())):
        lines.pop()
    content = "\n".join(lines).strip()

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(content + "\n")
    print(f"[OK] wrote {out} ({len(content)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
