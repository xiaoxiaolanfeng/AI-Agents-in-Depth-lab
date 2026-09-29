# 实验 3-2（Mem0 版）

> 对应 `ai-agent-book/chapter3/mem0/`

## 状态

⚠️ **本实验我们没有跑过**。这个目录只包含上游 `chapter3/mem0/` 的源码拷贝（9 个 Python 文件 + 配置 + README），供你按下面的步骤自己跑。

## Mem0 是什么

Mem0 是一个开源的"智能记忆层"框架（[mem0.ai](https://mem0.ai)）。它给 LLM 应用提供：

- **ADD-only 提取**：从对话增量提取 facts，不重复
- **合并 + 去重**：相同含义的事实自动合并
- **跨会话**：自动维持一致性、连续性、时序性
- **高利用率**：实验数据声称 26% 提升 LLM 响应准确率
- **本地或云端**：可自托管或用 Mem0 云服务

## 怎么跑

### 步骤 1：安装

```bash
cd src
python -m pip install -r requirements.txt
```

主要依赖：
- `mem0ai`（Mem0 框架）
- `openai`（LLM 调用）
- `pytest`（可选，跑测试用）

### 步骤 2：配置环境变量

```bash
# 用 Kimi 跑（推荐，跟原书一致）
export KIMI_API_KEY="sk-..."
# 或用 OpenAI 兼容接口
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"   # 自定义
```

具体配置参考 `src/env.example`。

### 步骤 3：跑 quickstart

```bash
python quickstart.py
```

### 步骤 4：跑 LOCOMO 基准

```bash
python main.py --mode benchmark
```

LOCOMO 是 Long Conversation Memory 的标准测试基准，包含 35 个长对话场景（每段约 50+ 轮）。

### 步骤 5：跟我们 3-1 对比

如果想跟 3-1（自己实现的 user-memory）做对比：

1. 把 `user-memory-evaluation/eval-data/real_eval_layer*.json` 用作输入
2. 改 `src/main.py` 让它接受我们 3-1 用的测试用例格式
3. 跑完后用 [`3-1-user-memory/eval-data/`](../3-1-user-memory/eval-data/) 里的 LLM judge 评估
4. 在 `analysis/` 写对比报告（目前还没有）

## 与 3-1 的对比维度

| 维度 | 3-1 自己实现 | 3-2 Mem0 |
| --- | --- | --- |
| 记忆存储 | 4 种模式（笔记/卡片/Advanced 卡片） | 框架内置 ADD-only |
| 提取时机 | 后台线程每 N 轮 | 增量式（每次对话后） |
| 工具调用 | ReAct + 显式 add/update/delete | 框架自动 |
| LOCOMO 基准 | 没跑 | 原书有 |
| 我们自己的真实评测 | ✅ 5 用例 × 4 mode = 20 次 | ⚠️ 未跑 |

## 文件清单

| 文件 | 职责 |
| --- | --- |
| `src/main.py` | 入口（quickstart / demo / benchmark / task） |
| `src/agent.py` | Mem0 + Kimi Agent |
| `src/config.py` | 配置 |
| `src/quickstart.py` | 快速试用 |
| `src/experiment.py` | 实验脚本 |
| `src/locomo_benchmark.py` | LOCOMO 基准 |
| `src/test_*.py` | 测试 |

详细说明见 `src/README.md`（来自上游）。

## 后续要做的事

1. **跑 LOCOMO 基准**：对比 Mem0 + 自己实现的 user-memory 谁在 LOCOMO 上更好
2. **跑我们的 5 用例**：跟 3-1 同套用例、同套评估脚本
3. **写对比报告**：Mem0 vs 自己实现的 4 维度对比（功能 / 性能 / 可控性 / 复杂度）