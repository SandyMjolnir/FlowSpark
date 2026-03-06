"""Tests for the effort estimator."""
import pytest

from flowspark.parser import AlteryxParser
from flowspark.mapper import ToolMapper
from flowspark.estimator import EffortEstimator, EFFORT_TABLE

from .fixtures import SIMPLE_WORKFLOW_XML, MACRO_WORKFLOW_XML


def _workflow(xml, name="test"):
    return AlteryxParser().parse_string(xml, name)


class TestEffortEstimatorBasic:
    def setup_method(self):
        self.wf = _workflow(SIMPLE_WORKFLOW_XML, "simple")
        self.mapped = ToolMapper().map_workflow(self.wf)
        self.estimator = EffortEstimator()

    def test_report_has_all_tools(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert len(report.tool_estimates) == len(self.wf.tools)

    def test_total_hours_positive(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.total_hours > 0

    def test_total_hours_sum(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        expected = sum(te.effort_hours for te in report.tool_estimates)
        assert abs(report.total_hours - expected) < 1e-6

    def test_complexity_set(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.complexity in ("low", "medium", "high", "very_high")

    def test_sprints_positive(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.estimated_sprints > 0

    def test_no_unsupported_in_simple_workflow(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.unsupported_count == 0

    def test_workflow_name_in_report(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.workflow_name == "simple"


class TestEffortEstimatorMacroAndUnsupported:
    def setup_method(self):
        self.wf = _workflow(MACRO_WORKFLOW_XML, "macro_wf")
        self.mapped = ToolMapper().map_workflow(self.wf)
        self.estimator = EffortEstimator()

    def test_unsupported_count_positive(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.unsupported_count >= 1

    def test_macro_count_positive(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        assert report.macro_count >= 1

    def test_notes_mention_unsupported(self):
        report = self.estimator.estimate(self.wf, self.mapped)
        combined = " ".join(report.notes)
        assert "manual" in combined.lower() or "unsupported" in combined.lower()


class TestEffortReport:
    def test_summary_contains_workflow_name(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML, "my_wf")
        mapped = ToolMapper().map_workflow(wf)
        report = EffortEstimator().estimate(wf, mapped)
        assert "my_wf" in report.summary()

    def test_dashboard_text_contains_totals(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML, "dash_wf")
        mapped = ToolMapper().map_workflow(wf)
        report = EffortEstimator().estimate(wf, mapped)
        dashboard = report.dashboard_text()
        assert "TOTAL" in dashboard
        assert "Sprints" in dashboard

    def test_as_dict_structure(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML, "dict_wf")
        mapped = ToolMapper().map_workflow(wf)
        report = EffortEstimator().estimate(wf, mapped)
        d = report.as_dict()
        assert "workflow_name" in d
        assert "total_hours" in d
        assert "tools" in d
        assert isinstance(d["tools"], list)

    def test_custom_sprint_hours(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML)
        mapped = ToolMapper().map_workflow(wf)
        estimator = EffortEstimator(sprint_hours=20.0)
        report = estimator.estimate(wf, mapped)
        expected = report.total_hours / 20.0
        assert abs(report.estimated_sprints - expected) < 1e-6


class TestEffortTable:
    def test_input_data_effort(self):
        assert EFFORT_TABLE["InputData"] == 0.5

    def test_join_higher_than_filter(self):
        assert EFFORT_TABLE["Join"] > EFFORT_TABLE["Filter"]

    def test_spatial_is_expensive(self):
        assert EFFORT_TABLE["Spatial"] >= 8.0
