"""Test the dataio running RMS spesici utility function for volumetrics"""

from pathlib import Path
from unittest import mock

import jsonschema
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from fmu import dataio
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.enums import StandardResultName
from fmu.dataio._models.standard_results.inplace_volumes import (
    InplaceVolumesResult,
    InplaceVolumesResultRow,
    InplaceVolumesSchema,
)
from fmu.dataio.export import _enums
from tests.utils import inside_rms

logger = null_logger(__name__)


VOLDATA_LEGACY = Path("tests/data/drogon/tabular/geogrid--vol.csv").absolute()
VOLDATA_STANDARD = Path("tests/data/drogon/tabular/volumes/geogrid.csv").absolute()

EXPECTED_COLUMN_ORDER = [
    "FLUID",
    "ZONE",
    "REGION",
    "FACIES",
    "LICENSE",
    "BULK",
    "NET",
    "PORV",
    "HCPV",
    "STOIIP",
    "GIIP",
    "ASSOCIATEDGAS",
    "ASSOCIATEDOIL",
]


@pytest.fixture(scope="package")
def voltable_legacy():
    return pd.read_csv(VOLDATA_LEGACY)


@pytest.fixture(scope="package")
def voltable_standard():
    return pd.read_csv(VOLDATA_STANDARD)


@pytest.fixture
def exportvolumetrics(
    mocked_rmsapi_modules,
    mock_project_variable,
    voltable_standard,
    monkeypatch,
    rmssetup_with_fmuconfig,
):
    # needed to find the global config at correct place
    monkeypatch.chdir(rmssetup_with_fmuconfig)

    from fmu.dataio.export.rms.inplace_volumes import _ExportVolumetricsRMS

    with mock.patch.object(
        _ExportVolumetricsRMS, "_get_table_with_volumes", return_value=voltable_standard
    ):
        yield _ExportVolumetricsRMS(mock_project_variable, "Geogrid", "geogrid_vol")


@inside_rms
def test_rms_volumetrics_export_class(exportvolumetrics):
    """See mocks in local conftest.py"""

    import rmsapi  # type: ignore # noqa
    import rmsapi.jobs as jobs  # type: ignore # noqa

    assert rmsapi.__version__ == "1.7"
    assert "Report" in jobs.Job.get_job("whatever").get_arguments.return_value

    # volume table name should be picked up by the mocked object
    assert exportvolumetrics._volume_table_name == "geogrid_volumes"

    out = exportvolumetrics._export_volume_table()

    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "volumes" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "restricted"


@inside_rms
def test_rms_volumetrics_export_class_table_index(voltable_standard, exportvolumetrics):
    """See mocks in local conftest.py"""

    out = exportvolumetrics._export_volume_table()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    # check that the table index is set correctly
    assert metadata["data"]["table_index"] == _enums.InplaceVolumes.index_columns()

    # should fail if missing table index
    exportvolumetrics._dataframe = voltable_standard.drop(columns="ZONE")
    with pytest.raises(KeyError, match="are not present"):
        exportvolumetrics._export_volume_table()


@inside_rms
def test_convert_table_from_legacy_to_standard_format(
    mock_project_variable,
    mocked_rmsapi_modules,
    voltable_standard,
    voltable_legacy,
    rmssetup_with_fmuconfig,
    monkeypatch,
):
    """Test that a voltable with legacy format is converted to
    the expected standard format"""

    from fmu.dataio.export.rms.inplace_volumes import _ExportVolumetricsRMS

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    # set the return value to be the table with legacy format
    # conversion to standard format should take place automatically
    with mock.patch.object(
        _ExportVolumetricsRMS,
        "_convert_table_from_rms_to_legacy_format",
        return_value=voltable_legacy.copy(),
    ):
        instance = _ExportVolumetricsRMS(
            mock_project_variable, "Geogrid", "geogrid_vol"
        )

    # the _dataframe attribute should now have been converted to standard
    pd.testing.assert_frame_equal(voltable_standard, instance._dataframe)

    # check that the exported table is equal to the expected
    out = instance._export_volume_table()
    # Note that using `read_parquet()` more than once in the same pytest module causes
    # errors due to an issue in pandas registering a type extension globally on every
    # invocation. This is probably a pandas bug.
    # https://github.com/apache/arrow/issues/41857
    exported_table = pd.read_parquet(out.items[0].absolute_path)

    pd.testing.assert_frame_equal(voltable_standard, exported_table)

    # check that NET is set equal to BULK
    assert "NET" not in voltable_legacy
    assert "NET" in exported_table
    assert np.allclose(exported_table["NET"], exported_table["BULK"])

    # check that the fluid column exists and contains oil and gas
    fluid_col = _enums.InplaceVolumes.TableIndexColumns.FLUID.value
    assert fluid_col in exported_table
    assert set(exported_table[fluid_col].unique()) == {"oil", "gas", "water"}

    # check the column order
    assert list(exported_table.columns) == EXPECTED_COLUMN_ORDER

    # check that the legacy format and the standard format gives
    # the same sum for volumetric columns
    hc_filter = exported_table["FLUID"].isin(["oil", "gas"])
    assert np.isclose(
        exported_table[hc_filter]["STOIIP"].sum(),
        voltable_legacy["STOIIP_OIL"].sum(),
    )
    assert np.isclose(
        exported_table[hc_filter]["GIIP"].sum(),
        voltable_legacy["GIIP_GAS"].sum(),
    )
    assert np.isclose(
        exported_table[hc_filter]["BULK"].sum(),
        (voltable_legacy["BULK_OIL"] + voltable_legacy["BULK_GAS"]).sum(),
    )
    assert np.isclose(
        exported_table[hc_filter]["PORV"].sum(),
        (voltable_legacy["PORV_OIL"] + voltable_legacy["PORV_GAS"]).sum(),
    )
    assert np.isclose(
        exported_table[hc_filter]["HCPV"].sum(),
        (voltable_legacy["HCPV_OIL"] + voltable_legacy["HCPV_GAS"]).sum(),
    )

    # make a random check for a particular row as well
    filter_query = (
        "REGION == 'WestLowland' and ZONE == 'Valysar' and FACIES == 'Channel'"
    )
    expected_bulk_for_filter = 8989826.15
    assert np.isclose(
        exported_table.query(filter_query + " and FLUID == 'oil'")["BULK"],
        expected_bulk_for_filter,
    )
    assert np.isclose(
        voltable_legacy.query(filter_query)["BULK_OIL"],
        expected_bulk_for_filter,
    )

    # the TOTAL column in the legacy table should equal
    # the sum of all fluids in the exported table
    assert np.isclose(
        voltable_legacy["BULK_TOTAL"].sum(),
        exported_table["BULK"].sum(),
    )
    assert np.isclose(
        voltable_legacy["PORV_TOTAL"].sum(),
        exported_table["PORV"].sum(),
    )
    # make a random check for a particular region and zone
    assert np.isclose(
        voltable_legacy.query(filter_query)["BULK_TOTAL"].sum(),
        exported_table.query(filter_query)["BULK"].sum(),
    )
    assert np.isclose(
        voltable_legacy.query(filter_query)["PORV_TOTAL"].sum(),
        exported_table.query(filter_query)["PORV"].sum(),
    )


@inside_rms
def test_net_column_equal_bulk_if_missing(exportvolumetrics, voltable_standard):
    """Test that the NET column is set equal to BULK if it is missing"""

    df_in = voltable_standard.copy()

    # remove the NET column
    # and check that NET is set equal to the BULK
    df_in = df_in.drop(columns="NET")
    df_out = exportvolumetrics._set_net_equal_to_bulk_if_missing_in_table(df_in)
    assert "NET" in df_out
    assert np.allclose(df_out["NET"], df_out["BULK"])

    # add a NET column with some values
    # and check that NET column is kept as is
    df_in["NET"] = df_out["BULK"] * 0.7
    df_out = exportvolumetrics._set_net_equal_to_bulk_if_missing_in_table(df_in)
    assert "NET" in df_out
    assert np.allclose(df_out["NET"], df_out["BULK"] * 0.7)


@pytest.mark.parametrize("volumetric_col", ["BULK", "PORV"])
def test_compute_water_zone_volumes_from_totals_oil_and_gas(
    exportvolumetrics, voltable_legacy, volumetric_col
):
    """
    Test that the method to compute water zone volumes works as expected by
    comparing the input and result table from the method.
    Here testing a table including both oil and gas.
    """

    df_in = voltable_legacy.copy()

    assert f"{volumetric_col}_TOTAL" in df_in
    assert f"{volumetric_col}_OIL" in df_in
    assert f"{volumetric_col}_GAS" in df_in
    assert f"{volumetric_col}_WATER" not in df_in

    df_out = exportvolumetrics._compute_water_zone_volumes_from_totals(df_in)

    assert f"{volumetric_col}_TOTAL" not in df_out
    assert f"{volumetric_col}_OIL" in df_out
    assert f"{volumetric_col}_GAS" in df_out
    assert f"{volumetric_col}_WATER" in df_out

    # water zone should be the same as the Total - HC
    assert np.isclose(
        (
            df_in[f"{volumetric_col}_TOTAL"]
            - df_in[f"{volumetric_col}_OIL"]
            - df_in[f"{volumetric_col}_GAS"]
        ).sum(),
        df_out[f"{volumetric_col}_WATER"].sum(),
    )

    # total zone should be the same as HC + water
    assert np.isclose(
        (
            df_out[f"{volumetric_col}_OIL"]
            + df_out[f"{volumetric_col}_GAS"]
            + df_out[f"{volumetric_col}_WATER"]
        ).sum(),
        df_in[f"{volumetric_col}_TOTAL"].sum(),
    )


@pytest.mark.parametrize("volumetric_col", ["BULK", "PORV"])
def test_compute_water_zone_volumes_from_totals_oil(
    exportvolumetrics, voltable_legacy, volumetric_col
):
    """
    Test that the method to compute water zone volumes works as expected by
    comparing the input and result table from the method.
    Here testing a table including only gas.
    """

    df_in = voltable_legacy.copy()

    # drop all OIL columns
    df_in = df_in.drop(columns=[col for col in df_in if col.endswith("_OIL")])

    assert f"{volumetric_col}_TOTAL" in df_in
    assert f"{volumetric_col}_OIL" not in df_in
    assert f"{volumetric_col}_GAS" in df_in
    assert f"{volumetric_col}_WATER" not in df_in

    df_out = exportvolumetrics._compute_water_zone_volumes_from_totals(df_in)

    assert f"{volumetric_col}_TOTAL" not in df_out
    assert f"{volumetric_col}_OIL" not in df_out
    assert f"{volumetric_col}_GAS" in df_out
    assert f"{volumetric_col}_WATER" in df_out

    # water zone should be the same as the Total - gas
    assert np.isclose(
        (df_in[f"{volumetric_col}_TOTAL"] - df_in[f"{volumetric_col}_GAS"]).sum(),
        df_out[f"{volumetric_col}_WATER"].sum(),
    )

    # total zone should be the same as gas + water
    assert np.isclose(
        (df_out[f"{volumetric_col}_GAS"] + df_out[f"{volumetric_col}_WATER"]).sum(),
        df_in[f"{volumetric_col}_TOTAL"].sum(),
    )


@pytest.mark.parametrize("volumetric_col", ["BULK", "PORV"])
def test_compute_water_zone_volumes_from_totals_gas(
    exportvolumetrics, voltable_legacy, volumetric_col
):
    """
    Test that the method to compute water zone volumes works as expected by
    comparing the input and result table from the method.
    Here testing a table including only oil.
    """

    df_in = voltable_legacy.copy()

    # drop all GAS columns
    df_in = df_in.drop(columns=[col for col in df_in if col.endswith("_GAS")])

    assert f"{volumetric_col}_TOTAL" in df_in
    assert f"{volumetric_col}_OIL" in df_in
    assert f"{volumetric_col}_GAS" not in df_in
    assert f"{volumetric_col}_WATER" not in df_in

    df_out = exportvolumetrics._compute_water_zone_volumes_from_totals(df_in)

    assert f"{volumetric_col}_TOTAL" not in df_out
    assert f"{volumetric_col}_OIL" in df_out
    assert f"{volumetric_col}_GAS" not in df_out
    assert f"{volumetric_col}_WATER" in df_out

    # water zone should be the same as the Total - gas
    assert np.isclose(
        (df_in[f"{volumetric_col}_TOTAL"] - df_in[f"{volumetric_col}_OIL"]).sum(),
        df_out[f"{volumetric_col}_WATER"].sum(),
    )

    # total zone should be the same as gas + water
    assert np.isclose(
        (df_out[f"{volumetric_col}_OIL"] + df_out[f"{volumetric_col}_WATER"]).sum(),
        df_in[f"{volumetric_col}_TOTAL"].sum(),
    )


def test_total_volumes_required(exportvolumetrics, voltable_legacy):
    """Test that the job fails if a required total volumes are missing"""

    df = voltable_legacy.copy()
    df = df.drop(columns=[col for col in df if col.endswith("_TOTAL")])

    with pytest.raises(RuntimeError, match="Found no 'Totals' volumes"):
        exportvolumetrics._compute_water_zone_volumes_from_totals(df)


@pytest.mark.parametrize("required_col", _enums.InplaceVolumes.required_columns())
def test_validate_table_required_col_missing(
    exportvolumetrics, voltable_standard, required_col
):
    """Test that the job fails if a required volumetric column is missing"""
    df = voltable_standard.drop(columns=required_col)
    exportvolumetrics._dataframe = df

    with pytest.raises(RuntimeError, match="missing"):
        exportvolumetrics._validate_table()


@pytest.mark.parametrize("required_col", ["BULK", "PORV", "HCPV"])
def test_validate_table_required_col_has_nan(
    exportvolumetrics, voltable_standard, required_col
):
    """Test that the job fails if a required volumetric column has nan values"""

    df = voltable_standard.copy()
    df[required_col] = np.nan

    exportvolumetrics._dataframe = df

    with pytest.raises(RuntimeError, match="missing"):
        exportvolumetrics._validate_table()


def test_validate_table_has_oil_or_gas(exportvolumetrics, voltable_standard):
    """Test that the job fails if a required volumetric column has nan values"""

    df = voltable_standard.copy()
    df = df[~df["FLUID"].isin(["oil", "gas"])]

    exportvolumetrics._dataframe = df

    with pytest.raises(RuntimeError, match="One or both 'oil' and 'gas'"):
        exportvolumetrics._validate_table()


def test_validate_table_has_oil_and_stoiip(exportvolumetrics, voltable_standard):
    """Test that the validation fails if oil columns are present but no STOIIP"""

    df = voltable_standard.copy()
    df = df.drop(columns="STOIIP")

    exportvolumetrics._dataframe = df

    with pytest.raises(RuntimeError, match="missing"):
        exportvolumetrics._validate_table()

    # validation should pass when no oil columns are present
    exportvolumetrics._dataframe = df[~(df["FLUID"] == "oil")]
    exportvolumetrics._validate_table()


def test_validate_table_has_gas_and_giip(exportvolumetrics, voltable_standard):
    """Test that the validations fails if gas columns are present but no GIIP"""

    df = voltable_standard.copy()
    df = df.drop(columns="GIIP")

    exportvolumetrics._dataframe = df

    with pytest.raises(RuntimeError, match="missing"):
        exportvolumetrics._validate_table()

    # validation should pass when no gas columns are present
    exportvolumetrics._dataframe = df[~(df["FLUID"] == "gas")]
    exportvolumetrics._validate_table()


def test_validate_table_against_pydantic_model_before_export(
    exportvolumetrics, voltable_standard
):
    """Test that the validation fails if the volumes table does not conform to the
    Pydantic model specifying the result."""

    df = voltable_standard.copy()
    exportvolumetrics._dataframe = df
    exportvolumetrics._validate_table()

    df["PORV"] = df["PORV"].replace(0.0, "a")
    exportvolumetrics._dataframe = df
    with pytest.raises(ValidationError, match="Input should be a valid number"):
        exportvolumetrics._validate_table()


@inside_rms
def test_rms_volumetrics_export_config_invalid(
    mock_project_variable,
    exportvolumetrics,
):
    """Test that an exception is raised if the config is invalid."""

    from fmu.dataio.export.rms.inplace_volumes import export_inplace_volumes

    with mock.patch(  # noqa
        "fmu.dataio.export.rms.inplace_volumes.load_global_config",
        return_value={},
    ):
        with pytest.raises(ValueError, match="valid config"):
            export_inplace_volumes(mock_project_variable, "Geogrid", "geogrid_volume")


@inside_rms
def test_rms_volumetrics_export_config_missing(
    mock_project_variable,
    mocked_rmsapi_modules,
    rmssetup_with_fmuconfig,
    monkeypatch,
):
    """Test that an exception is raised if the config is missing."""

    from fmu.dataio.export.rms import export_inplace_volumes
    from fmu.dataio.export.rms._utils import CONFIG_PATH

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    config_path_modified = Path("wrong.yml")

    CONFIG_PATH.rename(config_path_modified)

    with pytest.raises(FileNotFoundError, match="Could not detect"):
        export_inplace_volumes(mock_project_variable, "Geogrid", "geogrid_volume")

    # restore the global config file for later tests
    config_path_modified.rename(CONFIG_PATH)


@inside_rms
def test_rms_volumetrics_export_function(
    mock_project_variable,
    mocked_rmsapi_modules,
    voltable_standard,
    rmssetup_with_fmuconfig,
    monkeypatch,
):
    """Test the public function."""

    from fmu.dataio.export.rms import export_inplace_volumes
    from fmu.dataio.export.rms.inplace_volumes import _ExportVolumetricsRMS

    monkeypatch.chdir(rmssetup_with_fmuconfig)

    with mock.patch.object(
        _ExportVolumetricsRMS, "_get_table_with_volumes", return_value=voltable_standard
    ):
        result = export_inplace_volumes(
            mock_project_variable, "Geogrid", "geogrid_volume"
        )
    vol_table_file = result.items[0].absolute_path

    absolute_path = (
        rmssetup_with_fmuconfig.parent.parent
        / "share/results/tables/volumes/geogrid.parquet"
    )

    assert vol_table_file == absolute_path

    assert Path(vol_table_file).is_file()
    metadata = dataio.read_metadata(vol_table_file)
    logger.debug("Volume_table_file is %s", vol_table_file)

    assert "volumes" in metadata["data"]["content"]
    assert metadata["access"]["classification"] == "restricted"
    assert metadata["data"]["table_index"] == _enums.InplaceVolumes.index_columns()


@inside_rms
def test_inplace_volumes_payload_validates_against_model(
    exportvolumetrics,
    monkeypatch,
):
    """Tests that the volume table exported is validated against the payload result
    model."""

    out = exportvolumetrics._export_volume_table()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    InplaceVolumesResult.model_validate(df)  # Throws if invalid


@inside_rms
def test_inplace_volumes_payload_validates_against_schema(
    exportvolumetrics,
    monkeypatch,
):
    """Tests that the volume table exported is validated against the payload result
    schema."""

    out = exportvolumetrics._export_volume_table()
    df = (
        pq.read_table(out.items[0].absolute_path)
        .to_pandas()
        .replace(np.nan, None)
        .to_dict(orient="records")
    )
    jsonschema.validate(
        instance=df, schema=InplaceVolumesSchema.dump()
    )  # Throws if invalid


@inside_rms
def test_inplace_volumes_export_and_result_columns_are_the_same(
    mocked_rmsapi_modules,
) -> None:
    assert _enums.InplaceVolumes.table_columns() == list(
        InplaceVolumesResultRow.model_fields.keys()
    )


def test_that_required_columns_one_to_one_in_enums_and_schema() -> None:
    # It's valid for HCPV to be None for water, but nobody should be exporting only
    # water, therefore despite it being optional in the schema it will always be a
    # column.
    schema_required_fields = ["HCPV"]
    for field_name, field_info in InplaceVolumesResultRow.model_fields.items():
        if field_info.is_required():
            schema_required_fields.append(field_name)
    assert set(_enums.InplaceVolumes.required_columns()) == set(schema_required_fields)


def test_standard_result_in_metadata(exportvolumetrics):
    """Test that the standard result is set correctly in the metadata"""

    out = exportvolumetrics._export_volume_table()
    metadata = dataio.read_metadata(out.items[0].absolute_path)

    assert "standard_result" in metadata["data"]
    assert (
        metadata["data"]["standard_result"]["name"]
        == StandardResultName.inplace_volumes
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["version"]
        == InplaceVolumesSchema.VERSION
    )
    assert (
        metadata["data"]["standard_result"]["file_schema"]["url"]
        == InplaceVolumesSchema.url()
    )
