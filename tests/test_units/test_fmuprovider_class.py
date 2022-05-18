"""Test the _MetaData class from the _metadata.py module"""
import os

from fmu.dataio._fmu_provider import _FmuProvider, _get_folderlist
from fmu.dataio._utils import C, G, S, X

FOLDERTREE = "scratch/myfield/case/realization-13/iter-2"

CFG = dict()
CFG[X] = {"rootpath": ".", "casepath": ""}
CFG[S] = {}
CFG[G] = {}
CFG[C] = {}


def test_get_folderlist(fmurun):

    os.chdir(fmurun)
    mylist = _get_folderlist(fmurun)
    assert mylist[-1] == "iter-0"
    assert mylist[-3] == "ertrun1"


def test_fmuprovider_no_provider(testroot):
    """Testing the FmuProvider basics where no ERT context is found from folder tree."""

    os.chdir(testroot)
    myfmu = _FmuProvider(CFG)
    myfmu.detect_provider()

    assert myfmu.is_fmurun is False
    assert myfmu.case_name is None


def test_fmuprovider_ert2_provider(fmurun):
    """Testing the FmuProvider for an ERT2 case"""

    os.chdir(fmurun)

    CFG[S] = {"rootpath": fmurun, "casepath": None, "fmu_context": "forward"}
    CFG[X] = {"rootpath": fmurun, "casepath": None}

    myfmu = _FmuProvider(CFG)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0


def test_fmuprovider_detect_no_case_metadata(fmurun):
    """Testing the case metadata file which is not found here.

    That will still provide a file path but the metadata will be {} i.e. empty
    """
    os.chdir(fmurun)
    CFG[X] = {"rootpath": fmurun}

    myfmu = _FmuProvider(CFG)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert "fmu_case" in str(myfmu.case_metafile)
    assert not myfmu.case_metadata


def test_fmuprovider_detect_case_has_metadata(fmurun_w_casemetadata):
    """Testing the case metadata file which is found here"""
    CFG[X] = {"rootpath": fmurun_w_casemetadata}
    os.chdir(fmurun_w_casemetadata)
    myfmu = _FmuProvider(CFG)
    myfmu.detect_provider()
    assert myfmu.case_name == "ertrun1"
    assert myfmu.real_name == "realization-0"
    assert myfmu.real_id == 0
    assert "fmu_case" in str(myfmu.case_metafile)
    assert (
        myfmu.case_metadata["fmu"]["case"]["uuid"]
        == "a40b05e8-e47f-47b1-8fee-f52a5116bd37"
    )
