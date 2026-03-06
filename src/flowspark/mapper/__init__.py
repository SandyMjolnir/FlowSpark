"""Tool mapper: translates Alteryx tool categories to PySpark code snippets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from flowspark.parser import AlteryxWorkflow, AlteryxTool


@dataclass
class MappedTool:
    """The result of mapping a single :class:`AlteryxTool`."""

    tool_id: str
    category: str
    is_supported: bool
    pyspark_snippet: str
    notes: str = ""
    dependencies: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Supported categories and their PySpark templates
# ---------------------------------------------------------------------------

#: Short human-readable description for each supported category.
CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "InputData": "Read data from a file / JDBC source",
    "TextInput": "Inline data as a Spark DataFrame",
    "OutputData": "Write a DataFrame to a file / JDBC target",
    "Filter": "Filter rows using a boolean expression",
    "Formula": "Derive / transform columns",
    "MultiFieldFormula": "Apply the same formula to multiple fields",
    "Join": "Join two DataFrames on one or more keys",
    "Select": "Select, rename, or drop columns",
    "Sort": "Order rows by one or more columns",
    "Sample": "Limit or sample rows",
    "RecordID": "Append a sequential record identifier column",
    "Summarize": "Group-by aggregation",
    "Unique": "Deduplicate rows",
    "AppendFields": "Cross-join (append fields from one stream to every row)",
    "Union": "Stack multiple DataFrames vertically",
    "DataCleanse": "Standardise / cleanse text columns",
}

#: Categories that cannot yet be automatically translated.
UNSUPPORTED_CATEGORIES: set = {
    "Spatial",
    "FuzzyMatch",
    "FindReplace",
    "MacroInput",
    "MacroOutput",
    "FieldInfo",
}


#: File extension → Spark format mapping (used for both read and write).
_FILE_FORMAT_MAP: Dict[str, str] = {
    "csv": "csv",
    "xlsx": "com.crealytics.spark.excel",
    "xls": "com.crealytics.spark.excel",
    "parquet": "parquet",
    "json": "json",
    "avro": "avro",
}


def _snippet_input(tool: AlteryxTool) -> str:
    cfg = tool.configuration
    file_val = cfg.get("File", cfg.get("Alias", "path/to/input"))
    file_str = str(file_val).strip().strip('"')
    ext = file_str.rsplit(".", 1)[-1].lower() if "." in file_str else "csv"
    fmt = _FILE_FORMAT_MAP.get(ext, "csv")
    options = 'header="true", inferSchema="true"' if fmt == "csv" else ""
    options_str = f".options({options})" if options else ""
    return (
        f'# Tool {tool.tool_id}: InputData\n'
        f'df_{tool.tool_id} = spark.read.format("{fmt}"){options_str}.load("{file_str}")'
    )


def _snippet_text_input(tool: AlteryxTool) -> str:
    return (
        f'# Tool {tool.tool_id}: TextInput\n'
        f'# TODO: Replace with actual inline data\n'
        f'df_{tool.tool_id} = spark.createDataFrame([], schema=None)'
    )


def _snippet_output(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    file_val = cfg.get("File", cfg.get("Alias", "path/to/output"))
    file_str = str(file_val).strip().strip('"')
    ext = file_str.rsplit(".", 1)[-1].lower() if "." in file_str else "parquet"
    fmt = _FILE_FORMAT_MAP.get(ext, "parquet")
    return (
        f'# Tool {tool.tool_id}: OutputData\n'
        f'df_{source_id}.write.format("{fmt}").mode("overwrite").save("{file_str}")'
    )


def _snippet_filter(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    expr = cfg.get("Expression", "True")
    # Alteryx uses != for not-equal; PySpark accepts both != and <>.
    pyspark_expr = str(expr).replace("&&", "&").replace("||", "|")
    return (
        f'# Tool {tool.tool_id}: Filter\n'
        f'df_{tool.tool_id}_true = df_{source_id}.filter({pyspark_expr!r})\n'
        f'df_{tool.tool_id}_false = df_{source_id}.filter(~({pyspark_expr!r}))'
    )


def _snippet_formula(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    field_name = cfg.get("Field", {})
    if isinstance(field_name, dict):
        col_name = field_name.get("field", "new_column")
        expr = field_name.get("expression", "None")
    else:
        col_name = str(field_name)
        expr = cfg.get("Expression", "None")
    return (
        f'# Tool {tool.tool_id}: Formula\n'
        f'# Alteryx expression: {expr}\n'
        f'# TODO: Convert expression to PySpark SQL / Column API\n'
        f'df_{tool.tool_id} = df_{source_id}.withColumn("{col_name}", expr("{expr}"))'
    )


def _snippet_multi_field_formula(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    expr = cfg.get("Expression", "None")
    return (
        f'# Tool {tool.tool_id}: MultiFieldFormula\n'
        f'# Alteryx expression applied across multiple fields: {expr}\n'
        f'# TODO: Replace column list and expression with actual values\n'
        f'from pyspark.sql import functions as F\n'
        f'target_columns = []  # TODO: specify target columns\n'
        f'df_{tool.tool_id} = df_{source_id}\n'
        f'for col in target_columns:\n'
        f'    df_{tool.tool_id} = df_{tool.tool_id}.withColumn(col, F.expr("{expr}"))'
    )


def _snippet_join(tool: AlteryxTool, left_id: str, right_id: str) -> str:
    cfg = tool.configuration
    join_info = cfg.get("JoinInfo", {})
    if isinstance(join_info, dict):
        left_key = join_info.get("Left", "id")
        right_key = join_info.get("Right", "id")
    else:
        left_key = right_key = "id"
    return (
        f'# Tool {tool.tool_id}: Join\n'
        f'df_{tool.tool_id} = df_{left_id}.join(\n'
        f'    df_{right_id},\n'
        f'    df_{left_id}["{left_key}"] == df_{right_id}["{right_key}"],\n'
        f'    how="inner"  # TODO: verify join type (inner/left/right/outer)\n'
        f')'
    )


def _snippet_select(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    # SelectFields can be a nested dict or a list; we emit a generic stub.
    return (
        f'# Tool {tool.tool_id}: Select\n'
        f'# TODO: Specify columns to keep / rename\n'
        f'df_{tool.tool_id} = df_{source_id}.select("*")  # replace "*" with column list'
    )


def _snippet_sort(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    sort_info = cfg.get("SortInfo", {})
    if isinstance(sort_info, dict):
        col = sort_info.get("field", "id")
        order = sort_info.get("order", "Ascending")
    else:
        col = "id"
        order = "Ascending"
    asc = "True" if "asc" in str(order).lower() else "False"
    return (
        f'# Tool {tool.tool_id}: Sort\n'
        f'from pyspark.sql import functions as F\n'
        f'df_{tool.tool_id} = df_{source_id}.orderBy(F.col("{col}").asc() if {asc} else F.col("{col}").desc())'
    )


def _snippet_sample(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    n = cfg.get("N", cfg.get("Percent", "100"))
    mode = str(cfg.get("Mode", "First")).lower()
    if "percent" in mode or "random" in mode:
        fraction = float(str(n).replace("%", "")) / 100.0
        return (
            f'# Tool {tool.tool_id}: Sample\n'
            f'df_{tool.tool_id} = df_{source_id}.sample(fraction={fraction}, seed=42)'
        )
    return (
        f'# Tool {tool.tool_id}: Sample (first N rows)\n'
        f'df_{tool.tool_id} = df_{source_id}.limit({n})'
    )


def _snippet_record_id(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    col_name = cfg.get("FieldName", "RecordID")
    return (
        f'# Tool {tool.tool_id}: RecordID\n'
        f'from pyspark.sql import functions as F\n'
        f'from pyspark.sql.window import Window\n'
        f'df_{tool.tool_id} = df_{source_id}.withColumn(\n'
        f'    "{col_name}",\n'
        f'    F.row_number().over(Window.orderBy(F.monotonically_increasing_id()))\n'
        f')'
    )


def _snippet_summarize(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    return (
        f'# Tool {tool.tool_id}: Summarize\n'
        f'# TODO: Replace group_cols and agg_exprs with actual columns / aggregations\n'
        f'from pyspark.sql import functions as F\n'
        f'group_cols = []  # e.g. ["category"]\n'
        f'agg_exprs = []   # e.g. [F.sum("amount").alias("total_amount")]\n'
        f'df_{tool.tool_id} = df_{source_id}.groupBy(*group_cols).agg(*agg_exprs)'
    )


def _snippet_unique(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    return (
        f'# Tool {tool.tool_id}: Unique (deduplicate)\n'
        f'# TODO: Specify subset of columns if needed\n'
        f'df_{tool.tool_id} = df_{source_id}.dropDuplicates()'
    )


def _snippet_append_fields(tool: AlteryxTool, left_id: str, right_id: str) -> str:
    return (
        f'# Tool {tool.tool_id}: AppendFields (cross-join)\n'
        f'df_{tool.tool_id} = df_{left_id}.crossJoin(df_{right_id})'
    )


def _snippet_union(tool: AlteryxTool, source_ids: List[str]) -> str:
    if not source_ids:
        return f'# Tool {tool.tool_id}: Union – no sources detected'
    first, rest = source_ids[0], source_ids[1:]
    lines = [f'# Tool {tool.tool_id}: Union', f'df_{tool.tool_id} = df_{first}']
    for sid in rest:
        lines.append(f'df_{tool.tool_id} = df_{tool.tool_id}.unionByName(df_{sid})')
    return "\n".join(lines)


def _snippet_data_cleanse(tool: AlteryxTool, source_id: str) -> str:
    cfg = tool.configuration
    return (
        f'# Tool {tool.tool_id}: DataCleanse\n'
        f'from pyspark.sql import functions as F\n'
        f'# TODO: Apply cleansing rules defined in configuration: {cfg}\n'
        f'df_{tool.tool_id} = df_{source_id}  # replace with specific cleansing steps'
    )


def _snippet_unsupported(tool: AlteryxTool) -> str:
    return (
        f'# Tool {tool.tool_id}: *** UNSUPPORTED – {tool.category} ***\n'
        f'# Manual migration required. Alteryx plugin: {tool.tool_type}\n'
        f'# Configuration: {tool.configuration}\n'
        f'raise NotImplementedError("Tool {tool.tool_id} ({tool.category}) requires manual migration")'
    )


class ToolMapper:
    """Map every tool in an :class:`AlteryxWorkflow` to a :class:`MappedTool`.

    Usage::

        mapper = ToolMapper()
        mapped = mapper.map_workflow(workflow)
        for tool_id, mt in mapped.items():
            print(mt.pyspark_snippet)
    """

    def map_workflow(self, workflow: AlteryxWorkflow) -> Dict[str, MappedTool]:
        """Return a mapping from *tool_id* → :class:`MappedTool` for every tool.

        Each tool's PySpark snippet is generated based on the workflow's
        connection graph to resolve which upstream DataFrame(s) to use.
        """
        # Build adjacency: destination_tool_id → list of source_tool_ids
        incoming: Dict[str, List[str]] = {}
        for conn in workflow.connections:
            incoming.setdefault(conn.destination_tool_id, []).append(conn.source_tool_id)

        result: Dict[str, MappedTool] = {}
        for tool_id, tool in workflow.tools.items():
            sources = incoming.get(tool_id, [])
            mt = self._map_tool(tool, sources)
            # Propagate support flag back to the AlteryxTool in-place
            tool.is_supported = mt.is_supported
            tool.pyspark_category = mt.category
            result[tool_id] = mt
        return result

    def map_tool(self, tool: AlteryxTool, source_ids: Optional[List[str]] = None) -> MappedTool:
        """Map a single tool without workflow context."""
        return self._map_tool(tool, source_ids or [])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_tool(self, tool: AlteryxTool, source_ids: List[str]) -> MappedTool:
        cat = tool.category

        if cat in UNSUPPORTED_CATEGORIES:
            return MappedTool(
                tool_id=tool.tool_id,
                category=cat,
                is_supported=False,
                pyspark_snippet=_snippet_unsupported(tool),
                notes=f"No automatic mapping available for {cat}. Manual review required.",
            )

        src = source_ids[0] if source_ids else "source"
        snippet: str

        if cat == "InputData":
            snippet = _snippet_input(tool)
        elif cat == "TextInput":
            snippet = _snippet_text_input(tool)
        elif cat == "OutputData":
            snippet = _snippet_output(tool, src)
        elif cat == "Filter":
            snippet = _snippet_filter(tool, src)
        elif cat == "Formula":
            snippet = _snippet_formula(tool, src)
        elif cat == "MultiFieldFormula":
            snippet = _snippet_multi_field_formula(tool, src)
        elif cat == "Join":
            left = source_ids[0] if len(source_ids) > 0 else "left"
            right = source_ids[1] if len(source_ids) > 1 else "right"
            snippet = _snippet_join(tool, left, right)
        elif cat == "Select":
            snippet = _snippet_select(tool, src)
        elif cat == "Sort":
            snippet = _snippet_sort(tool, src)
        elif cat == "Sample":
            snippet = _snippet_sample(tool, src)
        elif cat == "RecordID":
            snippet = _snippet_record_id(tool, src)
        elif cat == "Summarize":
            snippet = _snippet_summarize(tool, src)
        elif cat == "Unique":
            snippet = _snippet_unique(tool, src)
        elif cat == "AppendFields":
            left = source_ids[0] if len(source_ids) > 0 else "left"
            right = source_ids[1] if len(source_ids) > 1 else "right"
            snippet = _snippet_append_fields(tool, left, right)
        elif cat == "Union":
            snippet = _snippet_union(tool, source_ids)
        elif cat == "DataCleanse":
            snippet = _snippet_data_cleanse(tool, src)
        else:
            return MappedTool(
                tool_id=tool.tool_id,
                category=cat,
                is_supported=False,
                pyspark_snippet=_snippet_unsupported(tool),
                notes=f"Unknown category '{cat}'. Manual review required.",
            )

        description = CATEGORY_DESCRIPTIONS.get(cat, cat)
        return MappedTool(
            tool_id=tool.tool_id,
            category=cat,
            is_supported=True,
            pyspark_snippet=snippet,
            notes=description,
            dependencies=list(source_ids),
        )
