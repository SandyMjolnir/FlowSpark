"""Shared test fixtures and sample XML."""

SIMPLE_WORKFLOW_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<AlteryxDocument yxmdVer="2022.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput">
        <Position x="54" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <File>data/input.csv</File>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxFilter.AlteryxFilter">
        <Position x="162" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Expression>[Age] > 18</Expression>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="3">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Formula.Formula">
        <Position x="270" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Field field="FullName" expression="[FirstName] + &quot; &quot; + [LastName]"/>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="4">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput">
        <Position x="378" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <File>data/output.csv</File>
        </Configuration>
      </Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="1" Connection="Output"/>
      <Destination ToolID="2" Connection="Input"/>
    </Connection>
    <Connection>
      <Origin ToolID="2" Connection="True"/>
      <Destination ToolID="3" Connection="Input"/>
    </Connection>
    <Connection>
      <Origin ToolID="3" Connection="Output"/>
      <Destination ToolID="4" Connection="Input"/>
    </Connection>
  </Connections>
</AlteryxDocument>
"""

JOIN_WORKFLOW_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<AlteryxDocument yxmdVer="2022.1">
  <Nodes>
    <Node ToolID="10">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput">
        <Position x="54" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <File>left.csv</File>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="11">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput">
        <Position x="54" y="162"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <File>right.csv</File>
        </Configuration>
      </Properties>
    </Node>
    <Node ToolID="12">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Join.Join">
        <Position x="270" y="108"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <JoinInfo Left="id" Right="id"/>
        </Configuration>
      </Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="10" Connection="Output"/>
      <Destination ToolID="12" Connection="Left"/>
    </Connection>
    <Connection>
      <Origin ToolID="11" Connection="Output"/>
      <Destination ToolID="12" Connection="Right"/>
    </Connection>
  </Connections>
</AlteryxDocument>
"""

MACRO_WORKFLOW_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<AlteryxDocument yxmdVer="2022.1">
  <Nodes>
    <Node ToolID="20">
      <GuiSettings Plugin="SomeMacro.yxmc">
        <Position x="54" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration/>
      </Properties>
    </Node>
    <Node ToolID="21">
      <GuiSettings Plugin="AlteryxSpatialPluginsGui.Spatial.Spatial">
        <Position x="162" y="54"/>
      </GuiSettings>
      <Properties>
        <Configuration/>
      </Properties>
    </Node>
  </Nodes>
  <Connections/>
</AlteryxDocument>
"""
