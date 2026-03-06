"""Tests for the Alteryx XML parser."""
import os
import tempfile

import pytest

from flowspark.parser import AlteryxParser, AlteryxWorkflow

from .fixtures import SIMPLE_WORKFLOW_XML, JOIN_WORKFLOW_XML, MACRO_WORKFLOW_XML


class TestAlteryxParserFromString:
    def _parse(self, xml: str, name: str = "test") -> AlteryxWorkflow:
        return AlteryxParser().parse_string(xml, name)

    def test_simple_workflow_tool_count(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML, "simple")
        assert len(wf.tools) == 4

    def test_simple_workflow_name(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML, "my_workflow")
        assert wf.name == "my_workflow"

    def test_tool_categories(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML)
        categories = {t.category for t in wf.tools.values()}
        assert "InputData" in categories
        assert "Filter" in categories
        assert "Formula" in categories
        assert "OutputData" in categories

    def test_connections_parsed(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML)
        assert len(wf.connections) == 3

    def test_connection_source_destination(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML)
        # First connection: tool 1 → tool 2
        first = wf.connections[0]
        assert first.source_tool_id == "1"
        assert first.destination_tool_id == "2"

    def test_join_workflow_two_inputs(self):
        wf = self._parse(JOIN_WORKFLOW_XML)
        assert len(wf.tools) == 3
        categories = [t.category for t in wf.tools.values()]
        assert categories.count("InputData") == 2
        assert "Join" in categories

    def test_macro_detected(self):
        wf = self._parse(MACRO_WORKFLOW_XML)
        assert len(wf.macros) >= 1
        assert "20" in wf.macros

    def test_spatial_tool_parsed(self):
        wf = self._parse(MACRO_WORKFLOW_XML)
        spatial_tool = wf.tools.get("21")
        assert spatial_tool is not None
        assert spatial_tool.category == "Spatial"

    def test_invalid_xml_raises(self):
        with pytest.raises(ValueError, match="Invalid XML"):
            AlteryxParser().parse_string("<not valid xml", "bad")

    def test_tool_position(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML)
        tool = wf.tools["1"]
        assert tool.position_x == 54.0
        assert tool.position_y == 54.0

    def test_input_file_in_configuration(self):
        wf = self._parse(SIMPLE_WORKFLOW_XML)
        tool = wf.tools["1"]
        assert "data/input.csv" in str(tool.configuration.get("File", ""))


class TestAlteryxParserFromFile:
    def test_parse_file_success(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yxmd", mode="w", encoding="utf-8", delete=False
        ) as fh:
            fh.write(SIMPLE_WORKFLOW_XML)
            path = fh.name
        try:
            wf = AlteryxParser().parse_file(path)
            assert len(wf.tools) == 4
        finally:
            os.unlink(path)

    def test_parse_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            AlteryxParser().parse_file("/nonexistent/path/workflow.yxmd")

    def test_workflow_name_from_filename(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yxmd", mode="w", encoding="utf-8", delete=False,
            prefix="my_workflow"
        ) as fh:
            fh.write(SIMPLE_WORKFLOW_XML)
            path = fh.name
        try:
            wf = AlteryxParser().parse_file(path)
            assert "my_workflow" in wf.name
        finally:
            os.unlink(path)
