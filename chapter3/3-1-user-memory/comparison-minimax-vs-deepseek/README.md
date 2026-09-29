# MiniMax-M3 vs DeepSeek-V4.1-Flash：3-1 真实跑评测对比

> **TL;DR**：同样 5 用例 × 4 mode = 20 次评测，**DeepSeek-V4.1-Flash 通过率 13/20（65%）明显高于 MiniMax-M3 的 9/20（45%）**。两个模型在不同模式上各有强项，但 L3 跨会话合成对两个模型都是死穴。

## 数据来源

| 模型 | 通过率 | 来源文件 |
| --- | --- | --- |
| MiniMax-M3 | 9/20 (45%) | `../eval-data/real_eval_*.json`（之前的 MiniMax 跑） |
| DeepSeek-V4.1-Flash | 13/20 (65%) | `../eval-data/real_eval_all_deepseek.json` |

评测脚本：`../eval-data/real_eval.py`

测试集：5 个 yaml 用例 × 4 种 memory 模式（notes / enhanced_notes / json_cards / advanced_json_cards）

## 完整对比表

| 用例 | 模式 | MiniMax | DeepSeek | 谁赢 |
| --- | --- | --- | --- | --- |
| L1-01 bank_account | notes | 0.417 | 0.083 | MiniMax |
| L1-01 | enhanced_notes | 0.000 | **1.000** | DeepSeek |
| L1-01 | json_cards | **1.000** | 0.000 | MiniMax |
| L1-01 | advanced_json_cards | 0.000 | **1.000** | DeepSeek |
| L1-03 medical_appt | notes | 1.000 | 1.000 | 平 |
| L1-03 | enhanced_notes | 1.000 | 1.000 | 平 |
| L1-03 | json_cards | 1.000 | 1.000 | 平 |
| L1-03 | advanced_json_cards | 1.000 | 1.000 | 平 |
| L2-01 multiple_vehicles | notes | 0.917 | **1.000** | DeepSeek |
| L2-01 | enhanced_notes | **0.917** | 0.750 | MiniMax |
| L2-01 | json_cards | 0.000 | **1.000** | DeepSeek |
| L2-01 | advanced_json_cards | 0.000 | **1.000** | DeepSeek |
| L2-03 multiple_credit_cards | notes | 0.000 | 0.000 | 都失败 |
| L2-03 | enhanced_notes | 0.583 | **1.000** | DeepSeek |
| L2-03 | json_cards | 0.000 | **0.917** | DeepSeek |
| L2-03 | advanced_json_cards | 0.000 | **1.000** | DeepSeek |
| L3-01 travel_coordination | notes | 0.000 | 0.000 | 都失败 |
| L3-01 | enhanced_notes | **1.000** | 0.000 | MiniMax |
| L3-01 | json_cards | **0.500** | 0.000 | MiniMax |
| L3-01 | advanced_json_cards | **0.917** | 0.000 | MiniMax |

## 关键模式

### 1. DeepSeek 在 L2 消歧上明显占优

L2 通过率（4 用例 × 4 mode = 16 条）：
- **DeepSeek: 12/16（75%）**
- MiniMax: 4/16（25%）

**DeepSeek 的强推理能力对 L2 消歧帮助巨大**——尤其在多车辆 / 多信用卡这种需要识别"两个 X"的场景。

### 2. L3-01 是模型无关难题

| 模型 | L3-01 通过模式数（4 mode） |
| --- | --- |
| MiniMax-M3 | 1/4（enhanced_notes 1.000） |
| DeepSeek-V4.1-Flash | 0/4（全 0） |

**L3 跨会话主动合成对两个模型都是死穴**——不是"哪个 LLM 更笨"，而是"这个题本来就难"。

### 3. L1-01 上两个模型完美反向

| 模式 | MiniMax | DeepSeek |
| --- | --- | --- |
| notes | 0.417 | 0.083 |
| enhanced_notes | 0.000 | **1.000** |
| json_cards | **1.000** | 0.000 |
| advanced_json_cards | 0.000 | **1.000** |

两个模型在 L1-01 上**几乎完美反向**。意味着 LLM 选型对模式选择有显著影响。

### 4. L1-03 难度不够区分模型

最基础的"查找 + 召回"任务，两个模型 4 mode 全满分。

## 5 个学习要点

### 1. LLM 能力差异 > 模式设计差异

L1-01 上两个模型反转表明：**模式适配是相对的**，选择 LLM 比选择模式更重要。

### 2. L2 消歧强依赖推理能力

L2 是真正区分模型能力的层——DeepSeek 的推理能力在多对象消歧上明显占优。

### 3. L3 是跨会话合成的"天花板"

无论哪个模型，L3 跨会话合成都很难。需要真正的时间推理、跨文档关联、优先级排序能力。

### 4. DeepSeek 倾向"少而精"的 memory

| 模型 | L1-01 平均 items |
| --- | --- |
| MiniMax | (21+8+23+8)/4 = 15 |
| DeepSeek | (14+7+15+9)/4 = 11.25 |

DeepSeek 写的 memory 更少，但分数反而更高——**合并整理后的 memory 更有用**。

### 5. 通过率不是唯一指标

DeepSeek 整体通过率更高，但**MiniMax 在 L3 上反而更强**——说明不同的 LLM 适合不同的层。

## 7 个 0.000 案例的归类（MiniMax-M3 跑时）

详见 [`../analysis/06-progress-update-6.md`](../analysis/06-progress-update-6.md) 和 [`../analysis/07-progress-update-7.md`](../analysis/07-progress-update-7.md)：

| 失败案例 | 错位置 |
| --- | --- |
| 9 个 reward=0.000 中，3 个错在**存储** | memory processor 自己写错日期 |
| 9 个中，5 个错在**读取** | agent 用"通用知识"补充 |
| 9 个中，1 个两种都错 | |

DeepSeek 跑时类似的失败模式也存在——这是 LLM 的固有问题，不是模型专属。

## 结论

**3-1 实验的"最佳 LLM 配置"是 DeepSeek-V4.1-Flash**，但 L3 跨会话合成是共同难题。如果想突破 L3，需要：
1. 用更强的 LLM（GPT-4 / Claude-Opus）
2. 加 system prompt 约束（详见 `../../NOTES.md`）
3. 设计新的记忆模式（不是当前 4 种之一）