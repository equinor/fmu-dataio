"""The conftest.py, providing magical fixtures to tests."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# retrieved from Drogon in RMS 14.2
VOLJOB_PARAMS = {
    "Input": [
        {
            "BulkVolumeProperty": [],
            "SelectedZoneNames": ["Valysar", "Therys", "Volon"],
            "RegionProperty": ["Grid models", "Geogrid", "Region"],
            "SelectedRegionNames": [
                "WestLowland",
                "CentralSouth",
                "CentralNorth",
                "NorthHorst",
                "CentralRamp",
                "CentralHorst",
                "EastLowland",
            ],
            "FaciesProperty": ["Grid models", "Geogrid", "FACIES"],
            "SelectedFaciesNames": [
                "Floodplain",
                "Channel",
                "Crevasse",
                "Coal",
                "Calcite",
                "Offshore",
                "Lowershoreface",
                "Uppershoreface",
            ],
            "LicenseBoundaries": [],
        }
    ],
    "Output": [
        {
            "Prefix": "",
            "UseOil": True,
            "UseGas": True,
            "UseTotals": True,
            "AreaAverage": False,
            "CreateDiscreteFluidProperty": False,
            "AcceptNegativeCellVolumes": False,
            "MapLayout": [],
            "MapOutput": "CLIPBOARD",
            "MapIncrementMultiplier": 1.0,
            "Calculations": [
                {
                    "Type": "BULK",
                    "CreateProperty": True,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
                {
                    "Type": "PORE",
                    "CreateProperty": True,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
                {
                    "Type": "HCPV",
                    "CreateProperty": False,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
                {
                    "Type": "STOIIP",
                    "CreateProperty": False,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
                {
                    "Type": "ASSOCIATED_GAS",
                    "CreateProperty": False,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
                {
                    "Type": "GIIP",
                    "CreateProperty": False,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
                {
                    "Type": "ASSOCIATED_LIQUID",
                    "CreateProperty": False,
                    "CreateZoneMap": False,
                    "CreateTotalMap": False,
                },
            ],
        }
    ],
    "Report": [
        {
            "ReportLayout": "TABULAR",
            "FileType": "EXCEL",
            "FileName": "",
            "AppendRelisationInfo": False,
            "UseRealizationNumber": True,
            "ExportUnits": False,
            "AddHeaders": False,
            "ScientificNotation": False,
            "DecimalCount": 2,
            "OutputGrouping": ["Zone", "Region index"],
            "ReportTableName": "geogrid_volumes",
        }
    ],
    "Variables": [
        {
            "Formation Variables": [
                {
                    "InputType": "ALL_ZONES_AND_REGIONS",
                    "InputSource": "TABLE",
                    "TableValues": 1.0,
                    "DataInput": [],
                    "Name": "NG",
                },
                {
                    "InputType": "ALL_ZONES_AND_REGIONS",
                    "InputSource": "TABLE",
                    "TableValues": 0.0,
                    "DataInput": [["Grid models", "Geogrid", "PHIT"]],
                    "Name": "POR",
                },
            ],
            "Gas Variables": [
                {
                    "InputType": "ALL_ZONES_AND_REGIONS",
                    "InputSource": "TABLE",
                    "TableValues": 0.0,
                    "DataInput": [["Grid models", "Geogrid", "SW"]],
                    "Name": "SW",
                },
                {
                    "InputType": "EACH_REGION",
                    "InputSource": "REGION_MODEL",
                    "TableValues": 0.0,
                    "DataInput": [],
                    "Name": "BG_FACTOR",
                },
                {
                    "InputType": "EACH_REGION",
                    "InputSource": "REGION_MODEL",
                    "TableValues": 0.0,
                    "DataInput": [],
                    "Name": "LGR_RATIO",
                },
            ],
            "Oil Variables": [
                {
                    "InputType": "EACH_REGION",
                    "InputSource": "REGION_MODEL",
                    "TableValues": 0.0,
                    "DataInput": [],
                    "Name": "GOC",
                },
                {
                    "InputType": "EACH_REGION",
                    "InputSource": "REGION_MODEL",
                    "TableValues": 0.0,
                    "DataInput": [],
                    "Name": "OWC",
                },
                {
                    "InputType": "ALL_ZONES_AND_REGIONS",
                    "InputSource": "TABLE",
                    "TableValues": 0.0,
                    "DataInput": [["Grid models", "Geogrid", "SW"]],
                    "Name": "SW",
                },
                {
                    "InputType": "EACH_REGION",
                    "InputSource": "REGION_MODEL",
                    "TableValues": 0.0,
                    "DataInput": [],
                    "Name": "BO_FACTOR",
                },
                {
                    "InputType": "EACH_REGION",
                    "InputSource": "REGION_MODEL",
                    "TableValues": 0.0,
                    "DataInput": [],
                    "Name": "GOR_RATIO",
                },
            ],
        }
    ],
}


@pytest.fixture
def mock_rmsapi():
    # Create a mock rmsapi module
    mock_rmsapi = MagicMock()
    mock_rmsapi.__version__ = "1.7"
    mock_rmsapi.jobs.Job.get_job(...).get_arguments.return_value = VOLJOB_PARAMS
    yield mock_rmsapi


@pytest.fixture
def mock_rmsapi_jobs():
    # Create a mock rmsapi.jobs module
    mock_rmsapi_jobs = MagicMock()
    yield mock_rmsapi_jobs


@pytest.fixture(autouse=True)
def mocked_rmsapi_modules(mock_rmsapi, mock_rmsapi_jobs):
    with patch.dict(
        sys.modules,
        {
            "rmsapi": mock_rmsapi,
            "rmsapi.jobs": mock_rmsapi_jobs,
        },
    ) as mocked_modules:
        yield mocked_modules


@pytest.fixture
def mock_project_variable():
    # A mock_project variable for the RMS 'project' (potentially extend for later use)
    mock_project = MagicMock()
    mock_project.horizons.representations = ["DS_final"]

    yield mock_project


@pytest.fixture
def xtgeo_surfaces(regsurf):
    regsurf_top = regsurf.copy()
    regsurf_top.name = "TopVolantis"

    regsurf_mid = regsurf.copy()
    regsurf_mid.name = "TopTherys"
    regsurf_mid.values += 100

    regsurf_base = regsurf.copy()
    regsurf_base.name = "TopVolon"
    regsurf_base.values += 200

    yield [regsurf_top, regsurf_mid, regsurf_base]
