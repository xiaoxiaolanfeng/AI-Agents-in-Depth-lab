# 实验 3-2（Memobase 版）

> 对应 `ai-agent-book/chapter3/memobase/`

## 状态

⚠️ **本实验我们没有跑过**。这个目录只包含上游 `chapter3/memobase/` 的源码拷贝（10 个 Python 文件 + 配置 + README），供你按下面的步骤自己跑。

## Memobase 是什么

Memobase（[github.com/memodb-io/memobase](https://github.com/memodb-io/memobase)）是一个轻量级的"用户画像 + 事件流"记忆框架。

跟 Mem0 的区别：
- **Mem0**：自动 ADD-only 提取，框架帮你总结
- **Memobase**：保留**结构化的事件（Event）**流，加上 Profile 总结，更像"事件溯源"

## 怎么跑

### 步骤 1：启动 Memobase 服务

Memobase 需要本地或远程的 Memobase 服务。可以：
- **官方云**（最简单）：[memobase.io](https://memobase.io) 注册账号拿 API key
- **本地部署**：`docker run -d -p 8019:8019 memodb/memobase-server`

### 步骤 2：安装 Python SDK

```bash
cd src
python -m pip install -r requirements.txt
```

主要依赖：
- `memobase>=0.0.27`（官方 SDK）
- `openai`（LLM 调用）
- `pytest`

### 步骤 3：配置环境变量

```bash
# 必填：Kimi Key（agent 用的 LLM）
export KIMI_API_KEY="sk-..."

# 如果用官方云
export MEMOBASE_PROJECT_URL="https://api.memobase.io"
export MEMOBASE_API_KEY="your-pm-key"

# 或本地服务
# export MEMOBASE_PROJECT_URL="http://localhost:8019"
```

### 步骤 4：跑 demo

```bash
# Profile demo（不需要外部 Memobase 服务）
python profile_demo.py

# 完整 demo（需要 Memobase 服务）
python quickstart.py
```

### 步骤 5：跑 LOCOMO 基准

```bash
python locomo_benchmark.py
```

### 步骤 6：跟 3-1 / Mem0 对比

跟 3-1 和 3-2-Mem0 一样的 5 用例跑一遍，对比三种实现。

## 记忆类型

| 类型 | 含义 |
| --- | --- |
| **Profile**（结构化） | 用户画像（facts + status） |
| **Event**（时间序列） | 事件流（带时间戳 + 描述） |
| **Contextual** | 上下文 |
| **Procedural** | 程序性记忆 |

Memobase 的核心思想是"Profile 是面向长期的稳定回答 + Event 是面向时间的变迁记录"。

## 与 3-1 / Mem0 的对比

| 维度 | 3-1 自己实现 | 3-2 Mem0 | 3-2 Memobase |
| --- | --- | --- | --- |
| 记忆粒度 | facts + cards | facts only | facts + events |
| 持久层 | 框架自带 | 框架自带 | **需要外部服务** |
| LOCOMO 支持 | ❌ | ✅ | ✅ |
| 我们自己跑 | ✅ 5 用例 | ⚠️ 未跑 | ⚠️ 未跑 |
| 上手难度 | 中 | 易 | 中（需起服务） |

## 文件清单

| 文件 | 职责 |
| --- | --- |
| `src/main.py` | 入口 |
| `src/agent.py` | MemobaseAgent + 手写记忆 store |
| `src/config.py` | 配置 |
| `src/profile_demo.py` | Profile 演示（无需外部服务） |
| `src/quickstart.py` | Quickstart |
| `src/locomo_benchmark.py` | LOCOMO 基准 |
| `src/test_*.py` | 测试 |

详细说明见 `src/README.md`（来自上游）。

## 后续要做的事

1. **起服务**（云或本地）
2. **跑 LOCOMO 基准**
3. **跑我们的 5 用例**
4. **写对比报告**：三种实现（自己 / Mem0 / Memobase）的横向对比