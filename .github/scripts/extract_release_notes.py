#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 UpdateLog.md 中提取指定 tag 版本对应的 Release Notes。

用法: python extract_release_notes.py <tag> [输出文件]
  <tag>    例如 v1.4.0（前导 v/V 可有可无，也兼容 refs/tags/v1.4.0 完整前缀）
  输出文件 默认 release_notes.md（写入当前工作目录）

提取范围: 从 `## vX.Y.Z` 标题开始，到下一个 `## vX.Y.Z` 标题（或文件末尾）之前，
包含中间的全部内容；并清理末尾的分隔线（---）与多余空行。

失败策略: 若 UpdateLog.md 中找不到与 tag 匹配的版本标题，直接以非零码退出，
并在 stderr 打印所有可用版本，避免生成只有版本号的无效 Release Notes。
"""
import re
import sys


def _norm_version(s: str) -> str:
    """归一化版本号: 去空白、去前导 v/V、兼容 refs/tags/ 等前缀。"""
    return s.strip().split("/")[-1].lstrip("vV")


def main() -> int:
    tag = _norm_version(sys.argv[1] if len(sys.argv) > 1 else "")
    out = (sys.argv[2] if len(sys.argv) > 2 else "release_notes.md").strip()
    print(f"[INFO] requested version: {tag}", file=sys.stderr)
    if not tag:
        print("[ERROR] missing version argument, usage: extract_release_notes.py <tag>", file=sys.stderr)
        return 1

    with open("UpdateLog.md", encoding="utf-8") as fh:
        text = fh.read()

    # 所有版本标题: `## v1.4.0` / `## v1.4.0 (2026-08-17)`
    headings = list(re.finditer(r"^##\s+v?([\d.]+)", text, re.M))
    available = [m.group(1).strip() for m in headings]
    print(f"[INFO] versions found in UpdateLog.md: {['v' + v for v in available] or ['(none)']}", file=sys.stderr)

    start = end = None
    for i, m in enumerate(headings):
        if m.group(1).strip() == tag:
            start = m.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            break

    if start is None:
        print(
            f"[ERROR] version v{tag} NOT FOUND in UpdateLog.md; "
            f"available versions: {['v' + v for v in available] or ['(none)']}",
            file=sys.stderr,
        )
        return 1

    content = text[start:end].strip()

    # 清理末尾的分隔线（---）与多余空行，正文内容保持原样
    lines = content.splitlines()
    while lines and (not lines[-1].strip() or re.fullmatch(r"-{3,}", lines[-1].strip())):
        lines.pop()
    content = "\n".join(lines).strip()

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(content + "\n")
    print(f"[OK] wrote {out} ({len(content)} chars)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
