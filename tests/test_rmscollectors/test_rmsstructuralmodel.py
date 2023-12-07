"""Test for RmsStructuralModel"""
import os
import yaml
import pytest
from pathlib import Path
from fmu.dataio.rmscollectors.structuralmodel import (
    RmsStructuralModelJob,
    RmsStructuralModel,
)
from fmu.dataio.rmscollectors.structuralmodel import (
    _extract_input_types,
    _extract_fault_info,
    _extract_surf_info,
    export_surfaces,
)

TEST_DATA = Path(__file__).parent / "../data/drogon/"


@pytest.fixture(name="geoframework")
def _fix_geo_volumes(drogon_project, write_yaml=False):
    """Return RmsStructuralModel object

    Args:
        drogon_project (roxar.Project): drogon project
        write_yaml (bool, optional): write yaml file of .params attribute. Defaults to False.

    Returns:
        RmsStructuralModel: results from job defined with names below
    """
    horizon_model = RmsStructuralModelJob(
        drogon_project, "DepthModelPostprocess", "GF", "depth_post_hum"
    )
    out_file = TEST_DATA / "rmscollectors/rmsstructuralmodel_params.yml"
    if write_yaml:
        with open(out_file, "w") as stream:
            yaml.dump(horizon_model.params, stream)

    return horizon_model


@pytest.fixture(name="structural_parameters", scope="session")
def _fix_structural_parameters():
    """Return parameter set originally extracted from drogon

    Raises:
        IOError: if cannot find test data

    Returns:
        dict: the parameter dictionary
    """
    # This parameter set is extracted from drogon rms project
    # rms version 13.1.2 linux based
    params = None
    inplace_params = TEST_DATA / "rmscollectors/rmsstructuralmodel_params.yml"
    with open(inplace_params, "r") as stream:
        params = yaml.load(stream, Loader=yaml.SafeLoader)

    if params is None:
        raise IOError(f"Cannot find parameters at {str(inplace_params)}")
    return params


def test_structural_model(drogon_project):
    sm_name = "DepthModelPostprocess"
    hm_name = "GF"
    structure = RmsStructuralModel(drogon_project, sm_name, hm_name)
    print(structure.horizons)


def test_extract_input_types(structural_parameters):
    input_representations = _extract_input_types(structural_parameters)
    print(input_representations)


def test_extract_faults(structural_parameters):
    fault_keys = ["displacement", "older_than", "constraints"]
    fault_info = _extract_fault_info(structural_parameters)
    assert isinstance(
        fault_info, dict
    ), f"Fault info should be dict but is {type(fault_info)}"
    assert (
        len(fault_info) == 6
    ), f"There should be 6 faults in test data, but is {len(fault_info)}"
    print(fault_info)
    for fault, info in fault_info.items():
        for key in info.keys():
            assert (
                key in fault_keys
            ), f"for fault: {fault} keyword |{key}| is not part of valid keys ({fault_keys})"


def test_extract_surf_info(structural_parameters):
    surf_info = _extract_surf_info(
        structural_parameters, _extract_input_types(structural_parameters)
    )
    print(surf_info)
    assert isinstance(
        surf_info, dict
    ), f"Surf info should be dict, but is {type(surf_info)}"
    assert len(surf_info) == 4, f"There are {len(surf_info)} surfaces, should be 4"


def test_export(
    drogon_project, structural_parameters, fmurun_w_casemetadata, DROGON_FMU_CONFIG
):
    rms_path = fmurun_w_casemetadata / "rms/model/"
    rms_path.mkdir(parents=True, exist_ok=True)
    os.chdir(rms_path)
    exported = export_surfaces(
        drogon_project,
        _extract_surf_info(
            structural_parameters,
            _extract_input_types(structural_parameters),
        ),
        DROGON_FMU_CONFIG,
    )
    print(exported)
