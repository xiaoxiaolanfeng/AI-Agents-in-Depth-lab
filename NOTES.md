# NOTES — 源码改动记录

> 本文件记录我们为了让 3-1 实验在 **MiniMax / DeepSeek 等 OpenAI 兼容 API** 上跑起来，对原书源码做的临时改动。所有改动**仅 1-2 行**，目的是让 base_url 走环境变量、不影响默认行为。

## 背景

原书 `chapter3/user-memory/` 的 5 个 provider（dashscope / siliconflow / doubao / kimi / openrouter）的 `base_url` 都是**硬编码字符串**：

```python
# 原代码（conversational_agent.py:116）
elif self.provider == "kimi" or self.provider == "moonshot":
    self.client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1"   # ← 硬编码
    )
```

这导致两个问题：
1. 没法用 Kimi 兼容的 OpenAI 兼容 API（MiniMax / DeepSeek）
2. 测试时需要改源码 + 还原

## 改动清单

### 改动 1：`chapter3/user-memory/conversational_agent.py`

```diff
 elif self.provider == "kimi" or self.provider == "moonshot":
     self.client = OpenAI(
         api_key=api_key,
-        base_url="https://api.moonshot.cn/v1"
+        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
     )
-    self.model = model or "kimi-k3"
+    self.model = model or os.environ.get("OPENAI_MODEL", "kimi-k3")
```

### 改动 2：`chapter3/user-memory/agent.py`

```diff
 elif self.provider == "kimi" or self.provider == "moonshot":
     self.client = OpenAI(
         api_key=api_key,
-        base_url="https://api.moonshot.cn/v1"
+        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
     )
-    self.model = model or "kimi-k3"
+    self.model = model or os.environ.get("OPENAI_MODEL", "kimi-k3")
```

## 改动的副作用

- **零副作用**（环境变量没设时）：默认值仍是 `https://api.moonshot.cn/v1` + `kimi-k3`，跟原书一致
- **副作用（设了环境变量）**：可以走任何 OpenAI 兼容 endpoint，包括：
  - `https://api.deepseek.com/v1` + model `deepseek-flash`
  - `https://api.minimax.cn/v1` + model `MiniMax-M3`
  - 任何其他 OpenAI 兼容服务

## 评测框架的兼容性

`chapter3/user-memory-evaluation/` 的 `LLMEvaluator` 走 openai SDK，本来就支持 `OPENAI_API_KEY` / `OPENAI_BASE_URL` 环境变量，**不用改源码**。

我们的评测脚本 `3-1-user-memory/eval-data/real_eval.py` 需要 monkey-patch `Config.get_evaluator_config` 方法，让它读环境变量：

```python
def _patched_get_evaluator_config(evaluator):
    return {"api_key": os.environ.get("OPENAI_API_KEY", ""),
            "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.minimax.cn/v1"),
            "model": os.environ.get("OPENAI_MODEL", "MiniMax-M3"),
            "type": "openai"}
UMConfig.get_evaluator_config = staticmethod(_patched_get_evaluator_config)
```

## 还原方法

如果想把代码还原成原书状态：

```bash
cd chapter3/user-memory
git diff conversational_agent.py agent.py
git checkout conversational_agent.py agent.py   # 完全还原
```

或者手动把 base_url 那行改回硬编码字符串。

## 系统提示词的潜在改进（未实施）

我们诊断过 9 个 reward=0.000 案例的根因（详见 `3-1-user-memory/analysis/07-progress-update-7.md`）：

1. **存储阶段错**（3 个）：memory processor 写错了日期/年份
2. **读取阶段错**（5 个）：agent 凭"通用知识"补充，memory 没读到源

**理论上**可以通过改 system prompt 减少失败：

```python
# 存储阶段（BackgroundMemoryProcessor）
"Preserve all numbers, dates, and named entities exactly as they appear
in the source conversation. Do not 'correct' or update them based on your own knowledge."

# 读取阶段（ConversationalAgent）
"Only state facts that are explicitly present in the user memories.
If information is missing, say so rather than inferring.
Do not supplement with general knowledge about credit cards, banks, travel, etc."
```

**但**由于我们的实验目标是**评估原书实验设计**，不是改进系统本身，所以**没有实施这些 prompt 改动**。如果你想验证 prompt 改进效果，可以在 `agent.py:162` 和 `conversational_agent.py:149` 的 `_init_system_prompt` 里加上上面这段，再重跑 `real_eval.py`。

## LLM 评委的选择说明

我们的实验里：
- **MiniMax-M3**：通过 `https://api.minimax.cn/v1` 调
- **DeepSeek-V4.1-Flash**：通过 `https://api.deepseek.com/v1` 调（model 名 `deepseek-flash`）

两者都是 OpenAI 兼容 API，可以无缝替换。脚本里通过环境变量配置：

```bash
# MiniMax
export OPENAI_API_KEY="sk-cp-..."
export OPENAI_BASE_URL="https://api.minimax.cn/v1"
export OPENAI_MODEL="MiniMax-M3"

# DeepSeek
export OPENAI_API_KEY="sk-6827ee4bd91c4be49b647df556802b5d"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_MODEL="deepseek-flash"
```

## 致谢

- 原书代码：https://github.com/bojieli/ai-agent-book
- 修改者：Mavis（AI agent）整理实验时
- 修改时间：2026-09