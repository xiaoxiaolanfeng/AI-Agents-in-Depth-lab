# Chapter 3 — Memory & RAG

> 对应《深入理解AI Agent》第 3 章：长期记忆 + RAG 的多种实现路径。

## 子实验

| 子实验 | 状态 | 简介 |
| --- | --- | --- |
| **[3-1-user-memory](./3-1-user-memory/)** | ✅ 已完成 | 长期用户记忆系统——对话侧 + 后台处理器 + 4 种 memory mode（含评测） |
| **[3-2-mem0](./3-2-mem0/)** | ✅ 已整理（未实跑） | 上游 Mem0 源码归档 + 运行说明 |
| **[3-2-memobase](./3-2-memobase/)** | ✅ 已整理（未实跑） | 上游 Memobase 源码归档 + 运行说明 |
| agentic-rag | ⏳ 待做 | Agentic RAG |
| agentic-rag-for-user-memory | ⏳ 待做 | RAG + 长期记忆混合 |
| contextual-retrieval | ⏳ 待做 | 上下文检索 |
| contextual-retrieval-for-user-memory | ⏳ 待做 | 上下文检索 + 长期记忆 |
| dense-embedding | ⏳ 待做 | 稠密向量检索 |
| sparse-embedding | ⏳ 待做 | 稀疏向量检索 |
| structured-index | ⏳ 待做 | 结构化索引 |
| structured-knowledge-extraction | ⏳ 待做 | 结构化知识抽取 |
| retrieval-pipeline | ⏳ 待做 | 检索管线 |
| log-sanitization | ⏳ 待做 | 记忆日志清洗 |
| user-memory-evaluation | ⏳ 待做 | 评测框架（在 3-1 里已部分使用） |

## 已完成实验摘要

### 3-1 长期用户记忆系统

架构：对话侧只读 + 后台处理器只写 + 4 种 memory mode（notes / enhanced_notes / json_cards / advanced_json_cards）。

评测：5 yaml × 4 mode = 20 次真实跑批。

| LLM judge | Pass Rate |
| --- | --- |
| MiniMax-M3 | 9 / 20 (45%) |
| DeepSeek-V4.1-Flash | 13 / 20 (65%) |

详见 [`3-1-user-memory/`](./3-1-user-memory/)。

### 3-2 现役记忆框架对照

- **Mem0**：[`3-2-mem0/`](./3-2-mem0/)——社区主流方案
- **Memobase**：[`3-2-memobase/`](./3-2-memobase/)——MemTensor 出品

两个仓库都已上传源码 + README，未实跑（需 mem0/memobase service + API key）。详细对比思路见 [`3-1-user-memory/analysis/08-3-1-vs-3-2.md`](./3-1-user-memory/analysis/08-3-1-vs-3-2.md)。

## 返回

← [仓库根 README](../../README.md)