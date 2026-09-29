"""Offline, deterministic metrics for the User Memory Evaluation Framework.

The LLM-as-judge evaluator in ``evaluator.py`` requires an API key and network
access. This module provides a complementary metric that runs fully offline on
canned data, so the benchmark can produce a scored comparison across memory
systems without calling any LLM.

The ``KeywordRecallEvaluator`` implements *key-fact recall*: for each test case a
set of gold facts (account numbers, confirmation codes, entity names, dates that
were actually stated in the conversation histories) is checked for presence in
the agent's response via normalized substring matching. The reward equals the
fraction of gold facts recalled, i.e. a classic answer-contains-gold recall
metric. It shares the ``EvaluationResult`` output shape with ``LLMEvaluator`` so
both metrics are interchangeable in the reporting/comparison code.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from models import TestCase, EvaluationResult


# A gold fact is either a single required string, or a list of acceptable
# variants (any one of which counts as a match, e.g. ["Feb 18", "February 18"]).
GoldFact = Union[str, List[str]]


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for tolerant substring matching."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _fact_matched(fact: GoldFact, normalized_response: str) -> bool:
    """Return True if the (possibly multi-variant) fact appears in the response."""
    variants = fact if isinstance(fact, list) else [fact]
    return any(_normalize(v) in normalized_response for v in variants)


def _fact_label(fact: GoldFact) -> str:
    """Human-readable label for a gold fact (first variant for any-of facts)."""
    if isinstance(fact, list):
        return fact[0] + (" (…)" if len(fact) > 1 else "")
    return fact


def load_gold_facts(path: Union[str, Path]) -> Dict[str, List[GoldFact]]:
    """Load gold-fact annotations from a JSON file.

    The file maps ``test_id`` to an object with a ``required_facts`` list. Each
    entry in ``required_facts`` is a string, or a list of acceptable variants.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    gold: Dict[str, List[GoldFact]] = {}
    for test_id, spec in data.items():
        if isinstance(spec, dict):
            gold[test_id] = spec.get("required_facts", [])
        elif isinstance(spec, list):
            gold[test_id] = spec
    return gold


class KeywordRecallEvaluator:
    """Offline key-fact recall metric (no LLM / API required)."""

    name = "keyword-recall"

    def __init__(self, gold_facts: Dict[str, List[GoldFact]]):
        """
        Args:
            gold_facts: Mapping of test_id -> list of gold facts to recall.
        """
        self.gold_facts = gold_facts

    def has_gold(self, test_id: str) -> bool:
        """Whether gold facts are available for the given test case."""
        return bool(self.gold_facts.get(test_id))

    def evaluate(
        self,
        test_case: TestCase,
        agent_response: str,
        extracted_memory: Optional[str] = None,
    ) -> EvaluationResult:
        """Score a response by the fraction of gold facts it recalls.

        The optional ``extracted_memory`` is concatenated with the response so a
        fact stated in the agent's memory dump also counts as recalled.
        """
        facts = self.gold_facts.get(test_case.test_id, [])
        haystack = _normalize(f"{agent_response}\n{extracted_memory or ''}")

        if not facts:
            return EvaluationResult(
                test_id=test_case.test_id,
                reward=0.0,
                passed=None,
                reasoning="No gold facts defined for this test case; skipped by keyword-recall metric.",
                required_info_found={},
            )

        info_found: Dict[str, float] = {}
        matched = 0
        for fact in facts:
            hit = _fact_matched(fact, haystack)
            info_found[_fact_label(fact)] = 1.0 if hit else 0.0
            matched += int(hit)

        recall = matched / len(facts)
        missing = [label for label, score in info_found.items() if score == 0.0]
        reasoning = f"Recalled {matched}/{len(facts)} gold facts."
        if missing:
            reasoning += " Missing: " + ", ".join(missing) + "."

        return EvaluationResult(
            test_id=test_case.test_id,
            reward=recall,
            passed=recall >= 0.8,
            reasoning=reasoning,
            required_info_found=info_found,
        )
