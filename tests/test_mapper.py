"""Tests for the tool mapper."""
import pytest

from flowspark.parser import AlteryxParser
from flowspark.mapper import ToolMapper, MappedTool, UNSUPPORTED_CATEGORIES

from .fixtures import SIMPLE_WORKFLOW_XML, JOIN_WORKFLOW_XML, MACRO_WORKFLOW_XML


def _workflow(xml):
    return AlteryxParser().parse_string(xml)


class TestToolMapperSimple:
    def setup_method(self):
        self.wf = _workflow(SIMPLE_WORKFLOW_XML)
        self.mapped = ToolMapper().map_workflow(self.wf)

    def test_all_tools_mapped(self):
        assert set(self.mapped.keys()) == set(self.wf.tools.keys())

    def test_input_data_supported(self):
        mt = self.mapped["1"]
        assert mt.is_supported is True
        assert mt.category == "InputData"

    def test_input_data_snippet_contains_spark_read(self):
        mt = self.mapped["1"]
        assert "spark.read" in mt.pyspark_snippet

    def test_filter_snippet(self):
        mt = self.mapped["2"]
        assert mt.is_supported is True
        assert "filter" in mt.pyspark_snippet.lower()

    def test_formula_snippet(self):
        mt = self.mapped["3"]
        assert mt.is_supported is True
        assert "withColumn" in mt.pyspark_snippet

    def test_output_data_snippet(self):
        mt = self.mapped["4"]
        assert mt.is_supported is True
        assert "write" in mt.pyspark_snippet

    def test_snippet_references_source_dataframe(self):
        # Tool 2 (Filter) should reference df_1 (its upstream)
        mt = self.mapped["2"]
        assert "df_1" in mt.pyspark_snippet

    def test_dependencies_tracked(self):
        mt = self.mapped["2"]
        assert "1" in mt.dependencies


class TestToolMapperJoin:
    def setup_method(self):
        self.wf = _workflow(JOIN_WORKFLOW_XML)
        self.mapped = ToolMapper().map_workflow(self.wf)

    def test_join_supported(self):
        mt = self.mapped["12"]
        assert mt.is_supported is True
        assert mt.category == "Join"

    def test_join_snippet_contains_join(self):
        mt = self.mapped["12"]
        assert ".join(" in mt.pyspark_snippet

    def test_join_references_both_inputs(self):
        mt = self.mapped["12"]
        assert "df_10" in mt.pyspark_snippet
        assert "df_11" in mt.pyspark_snippet


class TestToolMapperUnsupported:
    def setup_method(self):
        self.wf = _workflow(MACRO_WORKFLOW_XML)
        self.mapped = ToolMapper().map_workflow(self.wf)

    def test_spatial_unsupported(self):
        mt = self.mapped["21"]
        assert mt.is_supported is False

    def test_unsupported_snippet_has_not_implemented(self):
        mt = self.mapped["21"]
        assert "NotImplementedError" in mt.pyspark_snippet or "UNSUPPORTED" in mt.pyspark_snippet

    def test_unsupported_categories_constant(self):
        assert "Spatial" in UNSUPPORTED_CATEGORIES
        assert "FuzzyMatch" in UNSUPPORTED_CATEGORIES


class TestToolMapperSingleTool:
    """Test map_tool in isolation (no workflow context)."""

    def _tool(self, tool_id, plugin, config_xml="<Configuration/>"):
        import xml.etree.ElementTree as ET
        from flowspark.parser import AlteryxTool
        from flowspark.parser import _normalize_tool_type, _parse_configuration

        xml_str = f"""<Node ToolID="{tool_id}">
          <GuiSettings Plugin="{plugin}"><Position x="0" y="0"/></GuiSettings>
          <Properties>{config_xml}</Properties>
        </Node>"""
        node = ET.fromstring(xml_str)
        category = _normalize_tool_type(plugin)
        cfg = _parse_configuration(node)
        return AlteryxTool(
            tool_id=tool_id,
            tool_type=plugin,
            category=category,
            position_x=0,
            position_y=0,
            configuration=cfg,
        )

    def test_sort_snippet(self):
        tool = self._tool("99", "AlteryxBasePluginsGui.Sort.Sort")
        mt = ToolMapper().map_tool(tool, ["98"])
        assert "orderBy" in mt.pyspark_snippet

    def test_summarize_snippet(self):
        tool = self._tool("99", "AlteryxBasePluginsGui.Summarize.Summarize")
        mt = ToolMapper().map_tool(tool, ["98"])
        assert "groupBy" in mt.pyspark_snippet

    def test_union_snippet(self):
        tool = self._tool("99", "AlteryxBasePluginsGui.Union.Union")
        mt = ToolMapper().map_tool(tool, ["10", "11", "12"])
        assert "unionByName" in mt.pyspark_snippet

    def test_unique_snippet(self):
        tool = self._tool("99", "AlteryxBasePluginsGui.Unique.Unique")
        mt = ToolMapper().map_tool(tool, ["98"])
        assert "dropDuplicates" in mt.pyspark_snippet

    def test_record_id_snippet(self):
        tool = self._tool("99", "AlteryxBasePluginsGui.RecordID.RecordID")
        mt = ToolMapper().map_tool(tool, ["98"])
        assert "row_number" in mt.pyspark_snippet

    def test_sample_snippet(self):
        tool = self._tool("99", "AlteryxBasePluginsGui.Sample.Sample")
        mt = ToolMapper().map_tool(tool, ["98"])
        assert "limit" in mt.pyspark_snippet or "sample" in mt.pyspark_snippet
