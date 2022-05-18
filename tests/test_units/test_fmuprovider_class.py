"""Test the _MetaData class from the _metadata.py module"""
import os

import fmu.dataio as dio
from fmu.dataio._fmu_provider import _FmuProvider, _get_folderlist

FOLDERTREE = "scratch/myfield/case/realization-13/iter-2"


def test_get_folderlist(fmurun):

    os.chdir(fmurun)
    mylist = _get_folderlist(fmurun)
    assert mylist[-1] == "iter-0"
    assert mylist[-3] == "ertrun1"


def test_fmuprovider_no_provider(testroot, globalconfig1):
    """Testing the FmuProvider basics where no ERT context is found from folder tree."""

    os.chdir(testroot)
    ex = dio.ExportData(fmu_context="realization", config=globalconfig1)
    myfmu = _FmuProvider(ex)
    myfmu.detect_provider()

    assert myfmu.is_fmurun is False
    assert myfmu.case_name is None


def test_fmuprovider_ert2_provider(fmurun, globalconfig1):
    """Testing the FmuProvider for an ERT2 case"""

    os.chdir(fmurun)

    ex = dio.ExportData(fmu_context="realization", config=globalconfig1)
    ex._rootpath = fmurun

    myfmu = _FmuProvider(ex)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0


def test_fmuprovider_detect_no_case_metadata(fmurun, edataobj1):
    """Testing the case metadata file which is not found here.

    That will still provide a file path but the metadata will be {} i.e. empty
    """
    os.chdir(fmurun)
    edataobj1._runpath = fmurun

    myfmu = _FmuProvider(edataobj1)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert "fmu_case" in str(myfmu.case_metafile)
    assert not myfmu.case_metadata


def test_fmuprovider_detect_case_has_metadata(fmurun_w_casemetadata, edataobj1):
    """Testing the case metadata file which is found here"""
    edataobj1._rootpath = fmurun_w_casemetadata
    os.chdir(fmurun_w_casemetadata)
    myfmu = _FmuProvider(edataobj1)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert "fmu_case" in str(myfmu.case_metafile)
    assert (
        myfmu.case_metadata["fmu"]["case"]["uuid"]
        == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"
    )
