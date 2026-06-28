---
name: ingest
description: 将 raw/ 中的原始资料编译到 wiki/
---

# Ingest

1. 读取 raw/ 下指定文件
2. 提炼核心观点，写入 wiki/sources/ 或 wiki/concepts/ 或 wiki/entities/
3. 使用 org-roam 双向链接连接相关页面
4. 更新 wiki/index.org
5. 追加日志到 wiki/log.org
6. 将原始文件移到 raw/archive/
