"""The conftest.py, providing magical fixtures to tests."""

import sys
from unittest.mock import MagicMock

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


@pytest.fixture(autouse=True)
def mock_rmsapi_package(monkeypatch):
    # Create a mock rmsapi module
    mock_rmsapi = MagicMock()
    monkeypatch.setitem(sys.modules, "rmsapi", mock_rmsapi)
    mock_x_rmsapi = MagicMock()
    monkeypatch.setitem(sys.modules, "_rmsapi", mock_x_rmsapi)
    mock_rmsapi.__version__ = "1.7"
    mock_jobs_rmsapi = MagicMock()
    monkeypatch.setitem(sys.modules, "rmsapi.jobs", mock_jobs_rmsapi)

    mock_rmsapi.jobs.Job.get_job(...).get_arguments.return_value = VOLJOB_PARAMS
    yield mock_rmsapi, mock_x_rmsapi, mock_jobs_rmsapi


@pytest.fixture(autouse=True)
def mock_roxar_package(monkeypatch):
    # Create a mock roxar module (roxar is renamed to rmsapi from RMS 14.x)
    mock_roxar = MagicMock()
    monkeypatch.setitem(sys.modules, "roxar", mock_roxar)
    mock_x_roxar = MagicMock()
    monkeypatch.setitem(sys.modules, "_roxar", mock_x_roxar)
    mock_roxar.__version__ = "1.7"

    mock_roxar.jobs.Job.get_job(...).get_arguments.return_value = VOLJOB_PARAMS
    yield mock_roxar, mock_x_roxar


@pytest.fixture(autouse=True)
def mock_project_variable():
    # A mock_project variable for the RMS 'project' (potentially extend for later use)
    mock_project = MagicMock()

    yield mock_project
