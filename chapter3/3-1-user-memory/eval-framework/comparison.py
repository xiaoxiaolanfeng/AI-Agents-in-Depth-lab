"""Cross-system comparison for the User Memory Evaluation Framework.

Experiment 3-1 evaluates *memory systems*: the same three-layer test suite is run
against several memory configurations (e.g. Simple Notes vs. Advanced JSON Cards)
and their scores are compared side by side. This module takes a mapping of

    {system_name: {test_id: agent_response}}

scores every (system, test case) pair with the chosen metric, and renders a
scored comparison table broken down by layer plus an overall row - so the reader
can see, at a glance, which memory format wins on basic recall vs. cross-session
synthesis.
"""

from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from models import TestCase, EvaluationResult
from metrics import KeywordRecallEvaluator

console = Console()

LAYERS = ["layer1", "layer2", "layer3"]
LAYER_TITLES = {
    "layer1": "Layer 1 · Basic Recall",
    "layer2": "Layer 2 · Disambiguation",
    "layer3": "Layer 3 · Proactive Synthesis",
}


class ComparisonRunner:
    """Run one metric over several memory systems and compare their scores."""

    def __init__(
        self,
        framework,
        metric: str = "keyword-recall",
        gold_facts: Optional[Dict] = None,
        evaluator_type: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            framework: A loaded UserMemoryEvaluationFramework (for test-case lookup).
            metric: 'keyword-recall' (offline) or 'llm-judge' (needs API).
            gold_facts: Gold-fact annotations required by the keyword-recall metric.
            evaluator_type: Judge backend for 'llm-judge' (kimi/openai).
            model: Optional model override for 'llm-judge'.
        """
        self.framework = framework
        self.metric = metric
        self.gold_facts = gold_facts or {}
        self.evaluator_type = evaluator_type
        self.model = model
        self._evaluator = self._build_evaluator()

    def _build_evaluator(self):
        if self.metric == "keyword-recall":
            return KeywordRecallEvaluator(self.gold_facts)
        elif self.metric == "llm-judge":
            # Imported lazily so the offline path never requires the openai client.
            from evaluator import LLMEvaluator
            return LLMEvaluator(self.evaluator_type, model=self.model)
        raise ValueError(f"Unknown metric: {self.metric}. Supported: keyword-recall, llm-judge")

    def run(
        self,
        system_responses: Dict[str, Dict[str, str]],
        category: Optional[str] = None,
    ) -> Dict[str, Dict[str, EvaluationResult]]:
        """Score every system over the test cases it provides responses for.

        Args:
            system_responses: {system_name: {test_id: response}}.
            category: Optional layer filter (layer1/layer2/layer3).

        Returns:
            {system_name: {test_id: EvaluationResult}}
        """
        results: Dict[str, Dict[str, EvaluationResult]] = {}
        for system_name, responses in system_responses.items():
            if system_name.startswith("_"):
                continue  # skip JSON comment keys like "_comment"
            system_results: Dict[str, EvaluationResult] = {}
            for test_id, response in responses.items():
                test_case = self.framework.get_test_case(test_id)
                if not test_case:
                    console.print(f"[yellow]Skipping unknown test case: {test_id}[/yellow]")
                    continue
                if category and test_case.category != category:
                    continue
                if self.metric == "keyword-recall" and not self._evaluator.has_gold(test_id):
                    continue  # no gold facts -> not scorable offline
                system_results[test_id] = self._evaluator.evaluate(test_case, response)
            results[system_name] = system_results
        return results

    def _layer_of(self, test_id: str) -> str:
        test_case = self.framework.get_test_case(test_id)
        return test_case.category if test_case else "unknown"

    def _avg(self, results: Dict[str, EvaluationResult], layer: Optional[str] = None) -> Optional[float]:
        vals = [
            r.reward
            for tid, r in results.items()
            if layer is None or self._layer_of(tid) == layer
        ]
        return sum(vals) / len(vals) if vals else None

    def _count(self, results: Dict[str, EvaluationResult], layer: Optional[str] = None) -> int:
        return sum(1 for tid in results if layer is None or self._layer_of(tid) == layer)

    def build_table(self, results_by_system: Dict[str, Dict[str, EvaluationResult]]) -> Table:
        """Build a Rich comparison table (layers as rows, systems as columns)."""
        systems = list(results_by_system.keys())
        metric_label = "Keyword Recall" if self.metric == "keyword-recall" else "LLM-as-Judge Reward"
        table = Table(
            title=f"Memory System Comparison ({metric_label}, 0.000-1.000)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Layer", style="magenta", no_wrap=True)
        for system in systems:
            table.add_column(system, justify="center")

        for layer in LAYERS:
            row = [LAYER_TITLES[layer]]
            has_any = False
            for system in systems:
                avg = self._avg(results_by_system[system], layer)
                if avg is None:
                    row.append("—")
                else:
                    has_any = True
                    n = self._count(results_by_system[system], layer)
                    row.append(f"{avg:.3f} (n={n})")
            if has_any:
                table.add_row(*row)

        # Overall row
        overall = ["[bold]Overall[/bold]"]
        for system in systems:
            avg = self._avg(results_by_system[system])
            if avg is None:
                overall.append("—")
            else:
                n = self._count(results_by_system[system])
                overall.append(f"[bold]{avg:.3f} (n={n})[/bold]")
        table.add_section()
        table.add_row(*overall)
        return table

    def generate_report(self, results_by_system: Dict[str, Dict[str, EvaluationResult]]) -> str:
        """Generate a plain-text comparison report (for saving to --output)."""
        systems = list(results_by_system.keys())
        metric_label = "keyword-recall" if self.metric == "keyword-recall" else "llm-judge"
        lines = []
        lines.append("=" * 80)
        lines.append("MEMORY SYSTEM COMPARISON REPORT")
        lines.append(f"Metric: {metric_label} (score range 0.000-1.000)")
        lines.append("=" * 80)
        lines.append("")

        # Summary matrix
        header = f"{'Layer':<32}" + "".join(f"{s:>18}" for s in systems)
        lines.append(header)
        lines.append("-" * len(header))
        for layer in LAYERS:
            cells = []
            printed = False
            for system in systems:
                avg = self._avg(results_by_system[system], layer)
                if avg is None:
                    cells.append(f"{'—':>18}")
                else:
                    printed = True
                    n = self._count(results_by_system[system], layer)
                    cells.append(f"{avg:.3f} (n={n})".rjust(18))
            if printed:
                lines.append(f"{LAYER_TITLES[layer]:<32}" + "".join(cells))
        overall_cells = []
        for system in systems:
            avg = self._avg(results_by_system[system])
            overall_cells.append((f"{avg:.3f}" if avg is not None else "—").rjust(18))
        lines.append("-" * len(header))
        lines.append(f"{'Overall':<32}" + "".join(overall_cells))
        lines.append("")

        # Per-test-case detail
        all_test_ids = sorted({tid for r in results_by_system.values() for tid in r})
        lines.append("Per-test-case scores")
        lines.append("-" * len(header))
        lines.append(f"{'Test Case':<32}" + "".join(f"{s:>18}" for s in systems))
        for tid in all_test_ids:
            cells = []
            for system in systems:
                r = results_by_system[system].get(tid)
                cells.append((f"{r.reward:.3f}" if r else "—").rjust(18))
            lines.append(f"{tid:<32}" + "".join(cells))
        lines.append("")

        return "\n".join(lines)
