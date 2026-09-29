"""Real-run evaluation: feed evaluation YAML conversations into user-memory system,
collect responses from 4 memory modes, then LLM-judge each one.

Run from chapter3/user-memory directory."""
import json, os, sys, yaml, shutil, traceback
from pathlib import Path

# user-memory-evaluation modules; cwd IS user-memory so its modules win
USER_MEMORY = Path(r"D:\aitool\homework\deeplearn\ai-agent-book\chapter3\user-memory")
EVAL = Path(r"D:\aitool\homework\deeplearn\ai-agent-book\chapter3\user-memory-evaluation")
sys.path.insert(0, str(USER_MEMORY))
sys.path.insert(1, str(EVAL))
# Now evaluation's config.py takes precedence — but we need to monkey-patch it
# with our MiniMax key AFTER evaluation's framework loads.
USER_ID = "real_eval_user"

# Configure MiniMax via kimi interface
import config as um_config  # user-memory's config (cwd)
um_config.PROVIDER = "kimi"
um_config.MOONSHOT_API_KEY = os.environ["OPENAI_API_KEY"]
um_config.KIMI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.minimax.cn/v1")
um_config.KIMI_MODEL = "MiniMax-M3"

API_KEY = os.environ["OPENAI_API_KEY"]
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.minimax.cn/v1")
MODEL = os.environ.get("OPENAI_MODEL", "MiniMax-M3")

from conversational_agent import ConversationalAgent, ConversationConfig  # noqa: E402
from background_memory_processor import BackgroundMemoryProcessor, MemoryProcessorConfig  # noqa: E402
from config import MemoryMode, Config as UMConfig  # user-memory's config (cwd)

# user-memory's Config class is missing some fields evaluation's framework expects;
# monkey-patch defaults so import doesn't crash. Cover the full set evaluation
# reads at import time + at judge call time.
for _attr, _val in [
    ("MAX_RETRIES", 3),
    ("REQUEST_TIMEOUT", 60),
    ("TEST_CASES_DIR", ""),
    ("GOLD_FACTS_PATH", ""),
    ("SYSTEM_RESPONSES_PATH", ""),
    ("OPENAI_API_KEY", ""),
    ("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    ("OPENAI_MODEL", "gpt-4"),
    ("KIMI_API_KEY", ""),
    ("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
    ("KIMI_MODEL", "moonshot-v1-32k"),
    ("OPENROUTER_API_KEY", ""),
    ("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    ("DEFAULT_EVALUATOR", "kimi"),
]:
    if not hasattr(UMConfig, _attr):
        setattr(UMConfig, _attr, _val)

# Patch get_evaluator_config: route through whatever the env vars say (MiniMax or DeepSeek etc.)
def _patched_get_evaluator_config(evaluator):
    return {"api_key": os.environ.get("OPENAI_API_KEY", ""),
            "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.minimax.cn/v1"),
            "model": os.environ.get("OPENAI_MODEL", "MiniMax-M3"),
            "type": "openai"}
UMConfig.get_evaluator_config = staticmethod(_patched_get_evaluator_config)

MODE_STRINGS = {
    "notes": MemoryMode.NOTES,
    "enhanced_notes": MemoryMode.ENHANCED_NOTES,
    "json_cards": MemoryMode.JSON_CARDS,
    "advanced_json_cards": MemoryMode.ADVANCED_JSON_CARDS,
}
TARGETS = [
    "layer1_01_bank_account",
    "layer1_03_medical_appointment",
    "layer2_01_multiple_vehicles",
    "layer2_03_multiple_credit_cards",
    "layer3_01_travel_coordination",
]


def clear_disk_state(user_id):
    for d in [
        Path("data/memories"),
        Path("data/conversations"),
    ]:
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob(f"{user_id}*"):
            try:
                f.unlink()
            except Exception as e:
                print(f"  Could not delete {f}: {e}")


def count_memory_items(mm):
    """Count actual memory items persisted by a MemoryManager (post-process)."""
    if hasattr(mm, "notes"):
        return len(mm.notes)
    if hasattr(mm, "memory_cards"):
        return sum(
            len(subs) for cat in mm.memory_cards.values() for subs in cat.values()
        )
    if hasattr(mm, "categories"):
        return sum(len(cards) for cards in mm.categories.values())
    return -1


def snapshot_memory(mm):
    """Serialize the memory manager's current state to a JSON-friendly dict."""
    if hasattr(mm, "notes"):
        return {"type": "notes", "items": [n.to_dict() for n in mm.notes]}
    if hasattr(mm, "memory_cards"):
        return {"type": "json_cards", "items": mm.memory_cards}
    if hasattr(mm, "categories"):
        return {"type": "advanced_json_cards", "items": mm.categories}
    return {"type": "unknown", "items": None}


def run_one(test_id, mode_name):
    mode = MODE_STRINGS[mode_name]
    clear_disk_state(USER_ID)
    print(f"\n=== {test_id} | {mode_name} ===", flush=True)

    # Load test case via evaluation framework (sys.path has EVAL)
    from framework import UserMemoryEvaluationFramework  # evaluation's framework
    fw = UserMemoryEvaluationFramework(test_cases_dir=str(EVAL / "test_cases"))
    tc = fw.get_test_case(test_id)
    assert tc is not None

    # Override framework's judge config to use MiniMax
    import config as eval_config
    eval_config.Config.OPENAI_API_KEY = API_KEY
    eval_config.Config.OPENAI_BASE_URL = BASE_URL
    eval_config.Config.OPENAI_MODEL = MODEL
    eval_config.Config.DEFAULT_EVALUATOR = "openai"

    conv_config = ConversationConfig(
        enable_memory_context=True,
        enable_conversation_history=True,
    )

    agent = ConversationalAgent(
        user_id=USER_ID, api_key=API_KEY, provider="kimi", model=MODEL,
        config=conv_config, memory_mode=mode, verbose=False,
    )
    proc_config = MemoryProcessorConfig(
        conversation_interval=1, min_conversation_turns=1, output_operations=False,
    )
    processor = BackgroundMemoryProcessor(
        user_id=USER_ID, api_key=API_KEY, provider="kimi", model=MODEL,
        config=proc_config, memory_mode=mode, verbose=False,
    )

    # Feed conversation histories
    conv_contexts = []
    for history in tc.conversation_histories:
        ctx = []
        user_msg = None
        for msg in history.messages:
            if msg.role.value == "user":
                user_msg = msg.content
                ctx.append({"role": "user", "content": msg.content})
            elif msg.role.value == "assistant":
                ctx.append({"role": "assistant", "content": msg.content})
                if user_msg is not None and agent.conversation_history:
                    agent.conversation_history.add_turn(
                        session_id=f"eval_{history.conversation_id}",
                        user_message=user_msg,
                        assistant_message=msg.content,
                    )
                    user_msg = None
        conv_contexts.append(ctx)

    # Process memories
    results = processor.process_conversation_batch(conv_contexts)
    summary = {"added": 0, "updated": 0, "deleted": 0}
    for r in results:
        for k in summary:
            summary[k] += r.get("summary", {}).get(k, 0)
    # Force the processor's memory manager to reload from disk so we can
    # inspect what it actually wrote, then count real items.
    processor.memory_manager.load_memory()
    real_added = count_memory_items(processor.memory_manager)
    summary["real_items_in_memory"] = real_added
    snapshot = snapshot_memory(processor.memory_manager)
    print(f"  memory ops (from return): {summary}", flush=True)
    print(f"  real_items_in_memory = {real_added}", flush=True)

    # Fresh session
    agent.conversation_history.conversations = []
    agent.conversation = []
    agent._init_system_prompt()
    agent.memory_manager.load_memory()

    response = agent.chat(tc.user_question)
    print(f"  response ({len(response)} chars): {response[:200]}...", flush=True)

    result = fw.submit_and_evaluate(test_id, response, evaluator_type="openai")
    if result is None:
        return {"mode": mode_name, "response": response, "reward": None, "error": "judge None"}
    return {
        "mode": mode_name,
        "memory_ops": summary,
        "memory_snapshot": snapshot,
        "response": response,
        "reward": result.reward,
        "passed": (result.reward >= 0.6),
        "reasoning": result.reasoning,
        "required_info_found": result.required_info_found,
        "dimensions": {
            k: {"grade": v.grade.value, "score": v.score, "reasoning": v.reasoning}
            for k, v in (result.dimensions or {}).items()
        },
        "hallucination": (
            {"detected": result.hallucination.detected, "reasoning": result.hallucination.reasoning}
            if result.hallucination else None
        ),
    }


if __name__ == "__main__":
    out = {}
    from framework import UserMemoryEvaluationFramework
    fw = UserMemoryEvaluationFramework(test_cases_dir=str(EVAL / "test_cases"))

    for test_id in TARGETS:
        out[test_id] = {"modes": {}}
        tc = fw.get_test_case(test_id)
        out[test_id]["user_question"] = tc.user_question
        out[test_id]["expected_behavior"] = tc.expected_behavior
        out[test_id]["title"] = tc.title

        for mode_name in MODE_STRINGS:
            print(f"\n>>> {test_id} | {mode_name} <<<", flush=True)
            try:
                out[test_id]["modes"][mode_name] = run_one(test_id, mode_name)
                # Save incrementally after each mode so partial progress survives crashes
                Path(f"D:/aitool/homework/deeplearn/real_eval_{test_id}.json").write_text(
                    json.dumps(out[test_id], ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception as e:
                out[test_id]["modes"][mode_name] = {"error": f"{type(e).__name__}: {e}",
                                                    "traceback": traceback.format_exc()}
                Path(f"D:/aitool/homework/deeplearn/real_eval_{test_id}.json").write_text(
                    json.dumps(out[test_id], ensure_ascii=False, indent=2), encoding="utf-8"
                )

    # Also dump a combined file with all 5 test cases
    Path("D:/aitool/homework/deeplearn/real_eval_all.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved 5 test cases to real_eval_all.json")