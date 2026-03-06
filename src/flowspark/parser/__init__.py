"""Alteryx XML workflow parser."""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class AlteryxConnection:
    """Represents a directed connection between two nodes."""

    source_tool_id: str
    source_anchor: str
    destination_tool_id: str
    destination_anchor: str


@dataclass
class AlteryxTool:
    """Represents a single node (tool) inside an Alteryx workflow."""

    tool_id: str
    tool_type: str          # e.g. "AlteryxBasePluginsGui.DbFileInput.DbFileInput"
    category: str           # normalised short name, e.g. "InputData"
    position_x: float
    position_y: float
    configuration: Dict[str, Any] = field(default_factory=dict)
    annotation: str = ""

    # Populated by the mapper
    is_supported: bool = True
    pyspark_category: str = ""


@dataclass
class AlteryxWorkflow:
    """In-memory representation of a parsed Alteryx workflow."""

    name: str
    tools: Dict[str, AlteryxTool] = field(default_factory=dict)
    connections: List[AlteryxConnection] = field(default_factory=list)
    macros: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mapping from the verbose Alteryx plug-in class name to a short category
# used throughout the rest of FlowSpark.
# ---------------------------------------------------------------------------
_TOOL_TYPE_MAP: Dict[str, str] = {
    # Input / Output
    "AlteryxBasePluginsGui.DbFileInput.DbFileInput": "InputData",
    "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput": "OutputData",
    "AlteryxBasePluginsGui.TextInput.TextInput": "TextInput",
    # Transformation
    "AlteryxBasePluginsGui.AlteryxFilter.AlteryxFilter": "Filter",
    "AlteryxBasePluginsGui.Formula.Formula": "Formula",
    "AlteryxBasePluginsGui.MultiFieldFormula.MultiFieldFormula": "MultiFieldFormula",
    "AlteryxBasePluginsGui.Join.Join": "Join",
    "AlteryxBasePluginsGui.Select.Select": "Select",
    "AlteryxBasePluginsGui.Sort.Sort": "Sort",
    "AlteryxBasePluginsGui.Sample.Sample": "Sample",
    "AlteryxBasePluginsGui.RecordID.RecordID": "RecordID",
    "AlteryxBasePluginsGui.Summarize.Summarize": "Summarize",
    "AlteryxBasePluginsGui.Unique.Unique": "Unique",
    "AlteryxBasePluginsGui.AppendFields.AppendFields": "AppendFields",
    "AlteryxBasePluginsGui.Union.Union": "Union",
    # Join-like
    "AlteryxBasePluginsGui.FindReplace.FindReplace": "FindReplace",
    "AlteryxBasePluginsGui.Fuzzy.Fuzzy": "FuzzyMatch",
    # Spatial
    "AlteryxSpatialPluginsGui.Spatial.Spatial": "Spatial",
    # Macros
    "AlteryxGuiToolkit.Questions.Tab.Tab": "MacroInput",
    "AlteryxGuiToolkit.Questions.Tab.MacroOutput": "MacroOutput",
    # Data Quality
    "AlteryxBasePluginsGui.DataCleanse.DataCleanse": "DataCleanse",
    "AlteryxBasePluginsGui.FieldInfo.FieldInfo": "FieldInfo",
}

_MACRO_KEYWORDS = {"macro", "yxmc", ".yxmc"}


def _normalize_tool_type(plugin_name: str) -> str:
    """Return the short category for a plug-in class name.

    Falls back to the last dot-segment of *plugin_name* if the full name is
    not in the explicit mapping table.
    """
    if plugin_name in _TOOL_TYPE_MAP:
        return _TOOL_TYPE_MAP[plugin_name]
    parts = plugin_name.split(".")
    return parts[-1] if parts else plugin_name


def _parse_configuration(node: ET.Element) -> Dict[str, Any]:
    """Extract the <Configuration> block of a tool into a plain dict."""
    config: Dict[str, Any] = {}
    # Configuration may be a direct child or nested under <Properties>
    cfg_node = node.find("Configuration")
    if cfg_node is None:
        cfg_node = node.find("Properties/Configuration")
    if cfg_node is None:
        return config

    for child in cfg_node:
        # Recurse one level for nested elements; store text or a sub-dict.
        sub: Dict[str, Any] = {}
        for grandchild in child:
            sub[grandchild.tag] = grandchild.text or ""
        if sub:
            config[child.tag] = sub
        else:
            config[child.tag] = child.text or child.attrib or ""
    return config


def _parse_annotation(node: ET.Element) -> str:
    """Return the annotation string for a tool node, if present."""
    ann = node.find(".//Annotation/Name")
    if ann is not None and ann.text:
        return ann.text.strip()
    return ""


class AlteryxParser:
    """Parse Alteryx workflow XML files (.yxmd / .yxwz / .yxmc).

    Usage::

        parser = AlteryxParser()
        workflow = parser.parse_file("path/to/workflow.yxmd")
    """

    def parse_file(self, filepath: str) -> AlteryxWorkflow:
        """Parse an Alteryx workflow file and return an :class:`AlteryxWorkflow`.

        Parameters
        ----------
        filepath:
            Absolute or relative path to the ``.yxmd``, ``.yxwz``, or
            ``.yxmc`` workflow file.

        Raises
        ------
        FileNotFoundError
            If *filepath* does not exist.
        ValueError
            If the file cannot be parsed as valid XML.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Workflow file not found: {filepath}")

        try:
            tree = ET.parse(filepath)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML in {filepath}: {exc}") from exc

        root = tree.getroot()
        workflow_name = os.path.splitext(os.path.basename(filepath))[0]
        return self._parse_root(root, workflow_name)

    def parse_string(self, xml_content: str, name: str = "workflow") -> AlteryxWorkflow:
        """Parse an Alteryx workflow from an XML string.

        Parameters
        ----------
        xml_content:
            Raw XML text of the workflow.
        name:
            Logical name to assign to the resulting :class:`AlteryxWorkflow`.

        Raises
        ------
        ValueError
            If *xml_content* is not valid XML.
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML content: {exc}") from exc
        return self._parse_root(root, name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_root(self, root: ET.Element, name: str) -> AlteryxWorkflow:
        workflow = AlteryxWorkflow(name=name)
        self._parse_nodes(root, workflow)
        self._parse_connections(root, workflow)
        self._detect_macros(workflow)
        return workflow

    def _parse_nodes(self, root: ET.Element, workflow: AlteryxWorkflow) -> None:
        """Populate ``workflow.tools`` from the XML tree."""
        for node in root.iter("Node"):
            tool_id = node.get("ToolID", "")
            if not tool_id:
                continue

            gui_settings = node.find("GuiSettings")
            plugin = ""
            pos_x = 0.0
            pos_y = 0.0
            if gui_settings is not None:
                plugin = gui_settings.get("Plugin", "")
                position = gui_settings.find("Position")
                if position is not None:
                    try:
                        pos_x = float(position.get("x", 0))
                        pos_y = float(position.get("y", 0))
                    except (TypeError, ValueError):
                        pass

            category = _normalize_tool_type(plugin)
            configuration = _parse_configuration(node)
            annotation = _parse_annotation(node)

            tool = AlteryxTool(
                tool_id=tool_id,
                tool_type=plugin,
                category=category,
                position_x=pos_x,
                position_y=pos_y,
                configuration=configuration,
                annotation=annotation,
            )
            workflow.tools[tool_id] = tool

    def _parse_connections(self, root: ET.Element, workflow: AlteryxWorkflow) -> None:
        """Populate ``workflow.connections`` from the XML tree."""
        for conn in root.iter("Connection"):
            origin = conn.find("Origin")
            destination = conn.find("Destination")
            if origin is None or destination is None:
                continue

            workflow.connections.append(
                AlteryxConnection(
                    source_tool_id=origin.get("ToolID", ""),
                    source_anchor=origin.get("Connection", "Output"),
                    destination_tool_id=destination.get("ToolID", ""),
                    destination_anchor=destination.get("Connection", "Input"),
                )
            )

    def _detect_macros(self, workflow: AlteryxWorkflow) -> None:
        """Collect tool IDs that reference or represent macros."""
        for tool in workflow.tools.values():
            tool_lower = tool.tool_type.lower()
            if any(kw in tool_lower for kw in _MACRO_KEYWORDS):
                workflow.macros.append(tool.tool_id)
            # A reference to an external .yxmc file inside the configuration
            for val in tool.configuration.values():
                val_str = str(val).lower()
                if ".yxmc" in val_str and tool.tool_id not in workflow.macros:
                    workflow.macros.append(tool.tool_id)
