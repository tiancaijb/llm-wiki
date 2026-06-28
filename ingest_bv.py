#!/usr/bin/env python3
"""
从 B 站 BV 号自动生成 LLM Wiki 笔记。

用法:
  LLM_API_KEY=sk-xxx python3 ingest_bv.py BV1k6QvBYEVA

流程:
  1. bili-subtitle 下载字幕
  2. LLM 总结
  3. 写入 wiki/sources/ (org-roam 格式)
  4. 更新 index.org + log.org
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

import requests

WIKI_ROOT = Path.home() / "org" / "roam" / "llm-wiki"
CACHE_DIR = Path.home() / ".bilibili-subtitles"
API_BASE = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")


def get_api_key() -> str:
    key = os.environ.get("LLM_API_KEY", "")
    if not key:
        key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("❌ 需设置 LLM_API_KEY", file=sys.stderr)
        sys.exit(1)
    return key


def download_subtitle(bvid: str) -> dict:
    """调用 bili-subtitle 下载字幕，失败则尝试读缓存。"""
    import subprocess
    result = subprocess.run(
        ["bili-subtitle", bvid, "--json"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        json_path = CACHE_DIR / f"{bvid}.json"
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                return json.load(f)
    # 失败时尝试读缓存
    json_path = CACHE_DIR / f"{bvid}.json"
    if json_path.exists():
        print(f"  📦 使用缓存: {json_path}", file=sys.stderr)
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    print(f"❌ 下载失败: {result.stderr}", file=sys.stderr)
    sys.exit(1)


def summarize_with_llm(title: str, subtitles: list, key: str) -> str:
    """用 LLM 总结字幕，返回 org 格式笔记内容。"""
    # 组装字幕文本
    lines = []
    for item in subtitles:
        t = int(item.get("from", 0))
        content = item.get("content", "")
        lines.append(f"[{t // 60:02d}:{t % 60:02d}] {content}")
    transcript = "\n".join(lines)

    # 分块
    if len(transcript) > 5000:
        chunks = []
        remaining = transcript
        while len(remaining) > 5000:
            split = remaining.rfind("\n", 0, 5000)
            if split == -1:
                split = 5000
            chunks.append(remaining[:split])
            remaining = remaining[split + 1:]
        chunks.append(remaining)
    else:
        chunks = [transcript]

    summaries = []
    for i, chunk in enumerate(chunks):
        prompt = (
            f"请将以下B站视频字幕（第{i + 1}/{len(chunks)}部分）整理为结构化笔记：\n\n"
            f"{chunk}\n\n"
            f"要求：\n"
            f"- 保留关键的技术细节和具体数据\n"
            f"- 用标题组织层次结构\n"
            f"- 提取核心观点和可操作要点\n"
            f"- 直接用中文输出"
        )
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
            timeout=180,
        )
        resp.raise_for_status()
        summaries.append(resp.json()["choices"][0]["message"]["content"])
        print(f"  ✅ 第{i + 1}段总结完成", file=sys.stderr)

    if len(summaries) == 1:
        combined = summaries[0]
    else:
        parts = "\n\n---\n\n".join(f"## 第{i + 1}部分\n\n{s}" for i, s in enumerate(summaries))
        prompt = (
            f"请将以下多段视频笔记合并为一份完整结构化笔记。视频标题: {title}\n\n"
            f"{parts}\n\n"
            f"要求：去除重复、统一层级、保留所有关键信息。"
        )
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
            timeout=180,
        )
        resp.raise_for_status()
        combined = resp.json()["choices"][0]["message"]["content"]
        print(f"  ✅ 合并完成", file=sys.stderr)

    return combined


def slugify(text: str, max_len: int = 40) -> str:
    """从标题生成简短英文 slug。"""
    import re
    # 如果标题是 BV 号，尝试用前几个中文字
    if text.startswith("BV"):
        return text.lower()
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug.strip())[:max_len]
    return slug.strip("-")


def write_wiki_note(bvid: str, title: str, summary: str) -> tuple:
    """写入 wiki/sources/，返回 (uid, filename)。"""
    today = date.today().isoformat()
    uid = str(uuid.uuid4())
    slug = slugify(title)
    filename = f"{bvid.lower()}-{slug}.org"
    filepath = WIKI_ROOT / "wiki" / "sources" / filename

    content = (
        f":PROPERTIES:\n"
        f":ID:       {uid}\n"
        f":END:\n"
        f"#+TITLE: {title}\n"
        f"#+ROAM_TAGS: source video bilibili {bvid.lower()}\n"
        f"#+DATE: {today}\n"
        f"\n"
        f"BV: {bvid}\n"
        f"\n"
        f"{summary}\n"
        f"\n"
        f"** 关联链接\n"
        f"(暂无关联页面——知识库尚未建立连接)\n"
    )

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"  📝 笔记已写入: {filepath.relative_to(WIKI_ROOT)}", file=sys.stderr)
    return uid, filename, title


def update_index(filename: str, title: str, bvid: str):
    """在 index.org 的 Sources 分类下追加条目。"""
    index_path = WIKI_ROOT / "wiki" / "index.org"
    if not index_path.exists():
        return
    content = index_path.read_text(encoding="utf-8")
    entry = f"- [[file:sources/{filename}][{title}]] — B站视频 {bvid}\n"

    # 在 Sources 段落后追加
    marker = "** Syntheses\n"
    if marker in content:
        content = content.replace(marker, entry + marker)
    else:
        content += f"\n** Sources\n{entry}"

    index_path.write_text(content, encoding="utf-8")
    print(f"  📑 index.org 已更新", file=sys.stderr)


def update_log(bvid: str, title: str, uid: str, filename: str):
    """在 log.org 追加操作记录。"""
    log_path = WIKI_ROOT / "wiki" / "log.org"
    today = date.today().isoformat()

    entry = (
        f"\n** [{today}] ingest-from-bv | {title}\n"
        f"- BV: {bvid}\n"
        f"- 新增: [[id:{uid}][{title}]]（{filename}），更新 index\n"
        f"- 冲突: 无\n"
    )

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  📋 log.org 已更新", file=sys.stderr)


def git_commit(bvid: str, title: str):
    """自动 git commit。"""
    try:
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=WIKI_ROOT, capture_output=True, text=True, timeout=10,
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"ingest-from-bv: {bvid} {title[:60]}"],
            cwd=WIKI_ROOT, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            print(f"  ✅ git commit 完成", file=sys.stderr)
        else:
            # 可能没有变更
            pass
    except Exception as e:
        print(f"  ⚠ git commit 跳过: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="从 B 站视频生成 LLM Wiki 笔记")
    parser.add_argument("bvid", help="BV 号")
    args = parser.parse_args()

    bvid = args.bvid.upper()
    if not bvid.startswith("BV"):
        bvid = "BV" + bvid
    # BV 号大小写敏感，只确保前缀 BV
    if not bvid.startswith("BV"):
        bvid = "BV" + args.bvid
    else:
        bvid = "BV" + args.bvid[2:]  # 保留原始大小写

    print(f"🎬 {bvid}", file=sys.stderr)

    # 1. 下载字幕
    print("  📥 下载字幕...", file=sys.stderr)
    data = download_subtitle(bvid)
    title = data.get("title", bvid)
    subs = data.get("subtitles", [])
    print(f"  ✅ {len(subs)} 行字幕，标题: {title[:50]}", file=sys.stderr)

    # 2. 用 LLM 总结
    print("  🤖 LLM 总结中...", file=sys.stderr)
    key = get_api_key()
    summary = summarize_with_llm(title, subs, key)

    # 3. 写入 wiki/sources/
    print("  💾 写入知识库...", file=sys.stderr)
    uid, filename, _ = write_wiki_note(bvid, title, summary)

    # 4. 更新 index + log
    update_index(filename, title, bvid)
    update_log(bvid, title, uid, filename)

    # 5. git commit
    git_commit(bvid, title)

    roam_link = f"[[id:{uid}][{title}]]"
    print(f"\n✅ 完成！org-roam 链接:", file=sys.stderr)
    print(f"   {roam_link}", file=sys.stderr)
    print(f"   文件: {WIKI_ROOT / 'sources' / filename}", file=sys.stderr)
    # 输出到 stdout 方便复制
    print(roam_link)
    # 用 emacsclient 分窗打开（不抢占 pi 的 buffer）
    filepath = WIKI_ROOT / 'sources' / filename
    if filepath.exists():
        import subprocess
        escaped = str(filepath).replace('"', '\"')
        subprocess.Popen(["emacsclient", "-n", "-e",
                          f'(find-file-other-window "{escaped}")'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
