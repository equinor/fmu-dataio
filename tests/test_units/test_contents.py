"""Explicitly test all allowed contents."""

import pytest
from pydantic import ValidationError

from fmu.dataio._models.fmu_results import enums
from fmu.dataio.dataio import ExportData
from fmu.dataio.providers.objectdata._export_models import content_requires_metadata

# generic testing of functionality related to content is done elsewhere,
# mainly in test_dataio.py.


def test_content_facies_thickness(regsurf, globalconfig2):
    """Test export of the facies_thickness content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="facies_thickness",
    ).generate_metadata(regsurf)

    assert meta["data"]["content"] == "facies_thickness"


def test_content_fault_lines(polygons, globalconfig2):
    """Test export of the fault_lines content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="fault_lines",
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "fault_lines"


def test_content_fault_surface(tsurf, globalconfig2):
    """Test export of the fault_surface content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="fault_surface",
    ).generate_metadata(tsurf)

    assert meta["data"]["content"] == "fault_surface"


def test_fault_properties():
    # Tested in test_rms_context
    pass


def test_content_field_outline(polygons, globalconfig2):
    """Test export of the facies thickness content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="field_outline",
        content_metadata={"contact": "FWL"},
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "field_outline"


def test_content_field_region(polygons, globalconfig2):
    """Test export of the field_region content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="field_region",
        content_metadata={"id": 1},
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "field_region"
    assert meta["data"]["field_region"]["id"] == 1


def test_content_fluid_contact(regsurf, globalconfig2):
    """Test export of the fluid_contact content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="fluid_contact",
        content_metadata={"contact": "fwl"},
    ).generate_metadata(regsurf)

    assert meta["data"]["content"] == "fluid_contact"
    assert meta["data"]["fluid_contact"]["contact"] == "fwl"


def test_content_fluid_contact_case_insensitive(regsurf, globalconfig2):
    """Test export of the fluid_contact content."""
    with pytest.warns(UserWarning, match=r"contains uppercase.+value to 'owc'"):
        meta = ExportData(
            config=globalconfig2,
            name="MyName",
            content="fluid_contact",
            content_metadata={"contact": "OWC"},
        ).generate_metadata(regsurf)

    assert meta["data"]["fluid_contact"]["contact"] == "owc"


def test_content_fluid_contact_raises_on_invalid_contact(regsurf, globalconfig2):
    """Test export of the fluid_contact content."""
    with pytest.raises(ValidationError, match="FluidContact"):
        ExportData(
            config=globalconfig2,
            name="MyName",
            content="fluid_contact",
            content_metadata={"contact": "oec"},
        ).generate_metadata(regsurf)


def test_content_kh_product(regsurf, globalconfig2):
    """Test export of the khproduct content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="khproduct",
    ).generate_metadata(regsurf)

    assert meta["data"]["content"] == "khproduct"


def test_content_lift_curves(dataframe, globalconfig2):
    """Test export of the lift_curves content."""

    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="lift_curves",
    ).generate_metadata(dataframe)

    assert meta["data"]["content"] == "lift_curves"


def test_content_named_area(polygons, globalconfig2):
    """Test export of the named_area content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="named_area",
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "named_area"


def test_content_parameters(dataframe, globalconfig2):
    """Test export of the parameters content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="parameters",
    ).generate_metadata(dataframe)

    assert meta["data"]["content"] == "parameters"


def test_content_pinchout(polygons, globalconfig2):
    """Test export of the pinchout content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="pinchout",
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "pinchout"


def test_content_property(gridproperty, globalconfig2):
    """Test export of the property content."""
    # gives FutureWarning regarding missing geometry and content not being dict
    with pytest.warns(FutureWarning):
        meta = ExportData(
            config=globalconfig2,
            name="MyName",
            content="property",
        ).generate_metadata(gridproperty)

    assert meta["data"]["content"] == "property"


def test_content_property_as_dict(gridproperty, globalconfig2):
    """Test export of the property content."""
    content_specifc = {"attribute": "porosity", "is_discrete": False}
    # should give FutureWarning when not linked to a grid
    with pytest.warns(FutureWarning, match="linking it to a geometry"):
        meta = ExportData(
            config=globalconfig2,
            name="MyName",
            content="property",
            content_metadata=content_specifc,
        ).generate_metadata(gridproperty)

    assert meta["data"]["content"] == "property"
    assert meta["data"]["property"] == content_specifc


def test_content_seismic_as_dict(gridproperty, globalconfig2):
    """Test export of the property content."""
    content_specifc = {"attribute": "amplitude", "calculation": "mean"}

    with pytest.warns(FutureWarning, match="linking it to a geometry"):
        meta = ExportData(
            config=globalconfig2,
            name="MyName",
            content="seismic",
            content_metadata=content_specifc,
        ).generate_metadata(gridproperty)

    assert meta["data"]["content"] == "seismic"
    assert meta["data"]["seismic"] == content_specifc


def test_content_pvt(dataframe, globalconfig2):
    """Test export of the pvt content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="pvt",
    ).generate_metadata(dataframe)

    assert meta["data"]["content"] == "pvt"


def test_content_regions(polygons, globalconfig2):
    """Test export of the regions content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="regions",
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "regions"


def test_content_relperm(mock_relperm, globalconfig2):
    """Test export of the relperm content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="relperm",
    ).generate_metadata(mock_relperm)

    assert meta["data"]["content"] == "relperm"


def test_content_rft(polygons, globalconfig2):
    """Test export of the rft content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="rft",
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "rft"


def test_content_seismic(polygons, globalconfig2):
    """Test export of the seismic content."""

    # tested various other places


def test_content_simulationtimeseries(mock_summary, globalconfig2):
    """Test export of the simulationtimeseries content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="simulationtimeseries",
    ).generate_metadata(mock_summary)

    assert meta["data"]["content"] == "simulationtimeseries"


def test_content_subcrop(polygons, globalconfig2):
    """Test export of the subcrop content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="subcrop",
    ).generate_metadata(polygons)

    assert meta["data"]["content"] == "subcrop"


def test_content_thickness(regsurf, globalconfig2):
    """Test export of the thickness content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="thickness",
    ).generate_metadata(regsurf)

    assert meta["data"]["content"] == "thickness"


def test_content_time(polygons, globalconfig2):
    """Test export of the time content."""

    # tested various other places


def test_content_timeseries(mock_summary, globalconfig2):
    """Test export of the timeseries content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="timeseries",
    ).generate_metadata(mock_summary)

    assert meta["data"]["content"] == "timeseries"


def test_content_transmissibilities(dataframe, globalconfig2):
    """Test export of the transmissibilities content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="transmissibilities",
    ).generate_metadata(dataframe)

    assert meta["data"]["content"] == "transmissibilities"


def test_content_velocity(regsurf, globalconfig2):
    """Test export of the velocity content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="velocity",
    ).generate_metadata(regsurf)

    assert meta["data"]["content"] == "velocity"


def test_content_volumes(mock_volumes, globalconfig2):
    """Test export of the volumes content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="volumes",
    ).generate_metadata(mock_volumes)

    assert meta["data"]["content"] == "volumes"


def test_content_wellpicks(wellpicks, globalconfig2):
    """Test export of the wellpicks content."""
    meta = ExportData(
        config=globalconfig2,
        name="MyName",
        content="wellpicks",
    ).generate_metadata(wellpicks)

    assert meta["data"]["content"] == "wellpicks"


def test_content_requires_metadata():
    """Test the content_requires_metadata function"""

    # test contents that requires extra
    assert content_requires_metadata(enums.Content.field_outline)
    assert content_requires_metadata(enums.Content.field_region)
    assert content_requires_metadata(enums.Content.fluid_contact)
    assert content_requires_metadata(enums.Content.property)
    assert content_requires_metadata(enums.Content.seismic)

    # test some random contents that does not require extra
    assert not content_requires_metadata(enums.Content.depth)
    assert not content_requires_metadata(enums.Content.timeseries)
    assert not content_requires_metadata(enums.Content.volumes)
