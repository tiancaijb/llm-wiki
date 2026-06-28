# LLM Wiki — 项目配置

## 目录结构与权限

- `raw/` — 绝对只读。原始素材收件箱，禁止修改/删除
- `wiki/` — AI 专属工作区。创建、更新、提炼知识
- `assets/` — 媒体资源层

## 工作流

- `/ingest-from-bv <BV号>` — 下载 B 站字幕 → LLM 总结 → 生成 wiki 笔记
- `/ingest <路径>` — 读取 raw/ 文件 → 写入 wiki/ → 更新 index + log
- `/query <问题>` — 读 wiki/index.org → 定位 → 阅读 → 回答（用 org-roam ID 链接标注来源）
- `/lint` — 扫描孤岛页面、死链、知识冲突 → 报告（确认后才修复）

详细见 README.org 和对应的 pi skill。
