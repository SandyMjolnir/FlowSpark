"""Effort estimator: calculate migration effort and produce a planning report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from flowspark.parser import AlteryxWorkflow
from flowspark.mapper import MappedTool, UNSUPPORTED_CATEGORIES


# ---------------------------------------------------------------------------
# Effort model
# ---------------------------------------------------------------------------

#: Base effort in person-hours for each tool category.
EFFORT_TABLE: Dict[str, float] = {
    # Simple I/O
    "InputData": 0.5,
    "TextInput": 0.25,
    "OutputData": 0.5,
    # Basic transforms
    "Filter": 0.5,
    "Select": 0.25,
    "Sort": 0.25,
    "Sample": 0.25,
    "RecordID": 0.25,
    "Unique": 0.5,
    "DataCleanse": 1.0,
    # Medium complexity
    "Formula": 1.0,
    "MultiFieldFormula": 1.5,
    "Summarize": 1.0,
    "Union": 0.5,
    "AppendFields": 1.0,
    # High complexity
    "Join": 2.0,
    # Manual / unsupported
    "Spatial": 8.0,
    "FuzzyMatch": 8.0,
    "FindReplace": 4.0,
    "MacroInput": 4.0,
    "MacroOutput": 4.0,
    "FieldInfo": 1.0,
}

#: Complexity tier labels.
COMPLEXITY_TIERS = {
    "low": (0, 5),        # 0–5 hours total
    "medium": (5, 20),    # 5–20 hours
    "high": (20, 60),     # 20–60 hours
    "very_high": (60, float("inf")),
}

#: Sprint velocity: hours of migration work per sprint (default).
DEFAULT_SPRINT_HOURS = 40.0


def _effort_for_category(category: str) -> float:
    return EFFORT_TABLE.get(category, 2.0)  # default 2 h for unknown categories


@dataclass
class ToolEstimate:
    """Effort estimate for a single tool."""

    tool_id: str
    category: str
    is_supported: bool
    effort_hours: float
    reason: str


@dataclass
class EffortReport:
    """Full effort estimation report for a workflow."""

    workflow_name: str
    tool_estimates: List[ToolEstimate] = field(default_factory=list)
    total_hours: float = 0.0
    complexity: str = "low"
    estimated_sprints: float = 0.0
    unsupported_count: int = 0
    macro_count: int = 0
    notes: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"Effort Estimation – {self.workflow_name}",
            f"  Total tools      : {len(self.tool_estimates)}",
            f"  Unsupported tools: {self.unsupported_count}",
            f"  Macros detected  : {self.macro_count}",
            f"  Total effort     : {self.total_hours:.1f} hours",
            f"  Complexity       : {self.complexity.upper()}",
            f"  Estimated sprints: {self.estimated_sprints:.1f}",
        ]
        for note in self.notes:
            lines.append(f"  Note: {note}")
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "workflow_name": self.workflow_name,
            "total_hours": self.total_hours,
            "complexity": self.complexity,
            "estimated_sprints": self.estimated_sprints,
            "unsupported_count": self.unsupported_count,
            "macro_count": self.macro_count,
            "notes": self.notes,
            "tools": [
                {
                    "tool_id": te.tool_id,
                    "category": te.category,
                    "is_supported": te.is_supported,
                    "effort_hours": te.effort_hours,
                    "reason": te.reason,
                }
                for te in self.tool_estimates
            ],
        }

    def dashboard_text(self) -> str:
        """Return a plain-text effort dashboard suitable for CLI output."""
        bar_max = 40
        lines = [
            "=" * 60,
            f"  FlowSpark Effort Estimation Dashboard",
            f"  Workflow: {self.workflow_name}",
            "=" * 60,
            f"  {'Tool ID':<12} {'Category':<20} {'Hours':>6}  {'Bar'}",
            "-" * 60,
        ]
        max_h = max((te.effort_hours for te in self.tool_estimates), default=1)
        for te in self.tool_estimates:
            bar_len = int((te.effort_hours / max_h) * bar_max) if max_h else 0
            flag = " ⚠" if not te.is_supported else ""
            lines.append(
                f"  {te.tool_id:<12} {te.category:<20} {te.effort_hours:>5.1f}h  "
                f"{'█' * bar_len}{flag}"
            )
        lines += [
            "-" * 60,
            f"  {'TOTAL':<34} {self.total_hours:>5.1f}h",
            f"  Complexity: {self.complexity.upper():<10}  "
            f"Sprints: {self.estimated_sprints:.1f}",
            "=" * 60,
        ]
        if self.notes:
            lines.append("")
            for note in self.notes:
                lines.append(f"  ℹ  {note}")
        return "\n".join(lines)


class EffortEstimator:
    """Estimate migration effort for an Alteryx workflow.

    Usage::

        estimator = EffortEstimator()
        report = estimator.estimate(workflow, mapped)
        print(report.dashboard_text())
    """

    def __init__(self, sprint_hours: float = DEFAULT_SPRINT_HOURS):
        self.sprint_hours = sprint_hours

    def estimate(
        self,
        workflow: AlteryxWorkflow,
        mapped: Optional[Dict[str, MappedTool]] = None,
    ) -> EffortReport:
        """Calculate effort for *workflow*.

        Parameters
        ----------
        workflow:
            Parsed Alteryx workflow.
        mapped:
            Pre-computed :class:`MappedTool` dict (from
            :class:`~flowspark.mapper.ToolMapper`).  If *None* the estimator
            uses only the parser output.

        Returns
        -------
        EffortReport
        """
        report = EffortReport(
            workflow_name=workflow.name,
            macro_count=len(workflow.macros),
        )

        for tool_id, tool in workflow.tools.items():
            category = tool.category
            is_supported = category not in UNSUPPORTED_CATEGORIES

            if mapped and tool_id in mapped:
                is_supported = mapped[tool_id].is_supported

            effort = _effort_for_category(category)

            # Add overhead for each macro reference
            if tool_id in workflow.macros:
                effort += 2.0
                reason = f"Macro reference detected (+2 h overhead)"
            elif not is_supported:
                reason = f"Unsupported tool – full manual migration"
            else:
                reason = f"Automated migration"

            report.tool_estimates.append(
                ToolEstimate(
                    tool_id=tool_id,
                    category=category,
                    is_supported=is_supported,
                    effort_hours=effort,
                    reason=reason,
                )
            )
            if not is_supported:
                report.unsupported_count += 1

        report.total_hours = sum(te.effort_hours for te in report.tool_estimates)

        # Complexity tier
        for tier, (low, high) in COMPLEXITY_TIERS.items():
            if low <= report.total_hours < high:
                report.complexity = tier
                break

        report.estimated_sprints = (
            report.total_hours / self.sprint_hours if self.sprint_hours > 0 else 0.0
        )

        # Advisory notes
        if report.unsupported_count > 0:
            report.notes.append(
                f"{report.unsupported_count} tool(s) require manual migration – "
                "review ⚠️ items carefully before estimating further."
            )
        if report.macro_count > 0:
            report.notes.append(
                f"{report.macro_count} macro(s) detected – "
                "macro logic is not automatically translated."
            )
        if report.complexity in ("high", "very_high"):
            report.notes.append(
                "Consider breaking this workflow into smaller migration chunks."
            )

        return report
