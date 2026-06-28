---
name: llm-wiki
description: 管理 Karpathy 风格的 LLM Wiki 知识库（Emacs + org-roam）。当用户提到 LLM Wiki、知识库、ingest、query、lint，或要求将资料存入个人知识库时使用。
---

# LLM Wiki 知识库管理

项目路径: ~/projects/llm-wiki

基于 Karpathy LLM Wiki 理念，用 Emacs + org-roam + pi-coding-agent 构建。

## 工作流

### /ingest <路径>

摄取原始资料到知识库。

1. 读取 =~/projects/llm-wiki/raw/= 下指定文件
2. 提炼核心观点，写入 =wiki/sources/= 或 =wiki/concepts/= 或 =wiki/entities/=
3. 用 org-roam 链接连接相关页面
4. 更新 =wiki/index.org=（按分类加入目录条目）
5. 追加日志到 =wiki/log.org=：
   #+begin_src org
   ** [YYYY-MM-DD] ingest | <操作简述>
      - 变更: 新增 [[id:uuid][Page]]，更新 [[id:uuid][index]]
   #+end_src
6. 将原始文件移动到 =raw/archive/=

### /query <问题>

查询知识库回答问题。

1. 先读 =wiki/index.org= 定位相关内容
2. 深度阅读目标页面
3. 综合回答，用 org-roam 链接标注来源
4. 如果生成有价值内容，询问用户是否保存到 =wiki/syntheses/=
5. 如果保存，更新 index 和 log

### /lint

巡检知识库健康度（只生成报告，不修改）。

1. 读 =wiki/index.org= 和 =wiki/log.org=
2. 检查：
   - 孤岛页面（没有入链的 org-roam 笔记）
   - 死链（链接到不存在的页面）
   - 知识冲突（同一概念不同说法）
   - 老旧信息
3. 生成修复报告，用户确认后才执行修改

## 笔记规范

- 所有 wiki 页面用 org-mode，包含 =#+TITLE= 和 =#+ROAM_TAGS=
- 每个页面必须有 =** 关联链接= 章节
- Concepts/Entities: TitleCase 命名
- Sources/Syntheses: kebab-case 命名

## 本地化

- 项目在 WSL2 中，Emacs 用 =emacsclient= 操作
- org-roam 数据库自动更新，无需手动维护
- 文件写入后自动 git commit（=cd ~/projects/llm-wiki && git add -A && git commit -m ...=）
