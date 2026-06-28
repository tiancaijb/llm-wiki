---
name: lint
description: 巡检 wiki/ 知识库健康度
---

# Lint

只生成报告，不修改。用户确认后才执行修复。

1. 读 wiki/index.org 和 wiki/log.org
2. 检查：
   - 孤岛页面（没有入链的笔记）
   - 死链（链接不存在的页面）
   - 知识冲突（同一概念不同说法）
   - 老旧信息
3. 生成修复报告
