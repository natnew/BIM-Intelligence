"""In-memory variants of the minimal fixture for tests that need a known defect.

The committed ``minimal.ifc`` is read-only (C-04). Variants are derived from the generator so
each test states exactly how it differs from the baseline; nothing here is written to the
repository.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import ifcopenshell
import ifcopenshell.api.classification
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.type

from fixtures.make_minimal_ifc import build_minimal_ifc

Mutator = Callable[[ifcopenshell.file], None]

WALL_TYPE_GLOBAL_ID = "0WallType0000000000001"


def write_variant(directory: Path, name: str, mutate: Mutator) -> Path:
    """Write ``build_minimal_ifc()`` with ``mutate`` applied; return the file path."""
    model = build_minimal_ifc()
    mutate(model)
    return write_model(directory, name, model)


def write_model(directory: Path, name: str, model: ifcopenshell.file) -> Path:
    path = directory / name
    text: str = model.to_string()
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    return path


def wall(model: ifcopenshell.file, name: str) -> ifcopenshell.entity_instance:
    matches = [w for w in model.by_type("IfcWall") if w.Name == name]
    assert len(matches) == 1, name
    return matches[0]


def duplicate_w002_as_w001(model: ifcopenshell.file) -> None:
    """Two walls share one GlobalId (FR-VAL-06, D17)."""
    wall(model, "W-002").GlobalId = wall(model, "W-001").GlobalId


def malform_w003(model: ifcopenshell.file) -> None:
    wall(model, "W-003").GlobalId = "not-a-valid-guid"


def add_wall_type_with_inherited_properties(model: ifcopenshell.file) -> None:
    """A wall type carrying ``FireRating=REI 120`` and ``LoadBearing=True`` typed to W-001/W-002.

    W-001 keeps its own ``FireRating`` (instance wins); W-002 inherits the type's value.
    The type also carries a Uniclass reference that W-002 inherits but W-001 overrides,
    because IfcOpenShell resolves classification inheritance per system.
    """
    wall_type = ifcopenshell.api.root.create_entity(model, ifc_class="IfcWallType", name="WT-01")
    wall_type.GlobalId = WALL_TYPE_GLOBAL_ID
    pset = ifcopenshell.api.pset.add_pset(model, product=wall_type, name="Pset_WallCommon")
    ifcopenshell.api.pset.edit_pset(
        model, pset=pset, properties={"FireRating": "REI 120", "LoadBearing": True}
    )
    system = model.by_type("IfcClassification")[0]
    ifcopenshell.api.classification.add_reference(
        model,
        products=[wall_type],
        identification="Ss_25_10",
        name="Wall and barrier systems",
        classification=system,
    )
    ifcopenshell.api.type.assign_type(
        model, related_objects=[wall(model, "W-001"), wall(model, "W-002")], relating_type=wall_type
    )


IFC2X3_TEXT = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition[CoordinationView]'),'2;1');
FILE_NAME('legacy.ifc','2026-10-28T00:00:00',('fixtures'),('natnew'),'','','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCPERSON($,'Fixture',$,$,$,$,$,$);
#2=IFCORGANIZATION($,'BIM Intelligence',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'0.1','BIM Intelligence fixtures','bimi');
#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,$,$,1793577600);
#10=IFCPROJECT('2X3Project00000000001',#5,'Legacy',$,$,$,$,$,$);
#11=IFCSITE('2X3Site00000000000001',#5,'Site',$,$,$,$,$,.ELEMENT.,$,$,$,$,$);
#12=IFCBUILDING('2X3Building0000000001',#5,'B',$,$,$,$,$,.ELEMENT.,$,$,$);
#13=IFCBUILDINGSTOREY('2X3Storey000000000001',#5,'G',$,$,$,$,$,.ELEMENT.,0.);
#14=IFCRELAGGREGATES('2X3RelAgg000000000001',#5,$,$,#10,(#11));
#15=IFCRELAGGREGATES('2X3RelAgg000000000002',#5,$,$,#11,(#12));
#16=IFCRELAGGREGATES('2X3RelAgg000000000003',#5,$,$,#12,(#13));
#20=IFCWALL('2X3Wall00000000000001',#5,'W-2X3',$,$,$,$,$);
#21=IFCRELCONTAINEDINSPATIALSTRUCTURE('2X3RelCont00000000001',#5,$,$,(#20),#13);
#30=IFCPROPERTYSINGLEVALUE('IsExternal',$,IFCBOOLEAN(.T.),$);
#31=IFCPROPERTYSET('2X3Pset00000000000001',#5,'Pset_WallCommon',$,(#30));
#32=IFCRELDEFINESBYPROPERTIES('2X3RelDef000000000001',#5,$,$,(#20),#31);
#40=IFCCLASSIFICATION('NBS','2015',$,'Uniclass 2015');
#41=IFCCLASSIFICATIONREFERENCE($,'Ss_25_10_30','Wall systems',#40);
#42=IFCRELASSOCIATESCLASSIFICATION('2X3RelCls000000000001',#5,$,$,(#20),#41);
ENDSEC;
END-ISO-10303-21;
"""


def write_ifc2x3(directory: Path, name: str = "legacy.ifc") -> Path:
    """A hand-written IFC2X3 file: project → site → building → storey ``G``, one classified wall.

    Written as STEP text because IfcOpenShell's authoring API requires owner-history setup for
    IFC2X3; the literal keeps the fixture explicit and byte-deterministic.
    """
    path = directory / name
    path.write_text(IFC2X3_TEXT, encoding="utf-8", newline="\n")
    return path
