"""Test the dataio ExportData etc from the dataio.py module."""

import logging
import os
import pathlib
import sys
from copy import deepcopy

import pytest
import yaml
from fmu.dataio._utils import prettyprint_dict
from fmu.dataio.dataio import ExportData, ValidationError, read_metadata

# pylint: disable=no-member

logger = logging.getLogger(__name__)


def pydantic_warning() -> str:
    return r"""The global configuration has one or more errors that makes it
impossible to create valid metadata. The data will still be exported but no
metadata will be made. You are strongly encouraged to correct your
configuration. Invalid configuration may be disallowed in future versions.

Detailed information:
\d+ validation error(s)? for GlobalConfiguration
"""


def test_generate_metadata_simple(globalconfig1):
    """Test generating metadata"""

    default_fformat = ExportData.grid_fformat
    ExportData.grid_fformat = "grdecl"

    logger.info("Config in: \n%s", globalconfig1)

    edata = ExportData(config=globalconfig1, content="depth")

    assert edata.config["model"]["name"] == "Test"

    assert edata.meta_format == "yaml"
    assert edata.grid_fformat == "grdecl"
    assert edata.name == ""

    ExportData.grid_fformat = default_fformat  # reset


def test_missing_or_wrong_config_exports_with_warning(regsurf):
    """In case a config is missing, or is invalid, do export with warning."""

    with pytest.warns(UserWarning, match=pydantic_warning()):
        edata = ExportData(config={}, content="depth")

    with pytest.warns(UserWarning, match=pydantic_warning()):
        meta = edata.generate_metadata(regsurf)

    assert "masterdata" not in meta

    with pytest.warns(UserWarning, match=pydantic_warning()):
        out = edata.export(regsurf, name="mysurface")

    assert "mysurface" in out

    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


def test_config_miss_required_fields(globalconfig1, regsurf):
    """Global config exists but missing critical data; export file but skip metadata."""

    cfg = globalconfig1.copy()

    del cfg["access"]
    del cfg["masterdata"]
    del cfg["model"]

    with pytest.warns(UserWarning, match=pydantic_warning()):
        edata = ExportData(config=cfg, content="depth")

    with pytest.warns(UserWarning):
        out = edata.export(regsurf, name="mysurface")

    assert "mysurface" in out

    with pytest.raises(OSError, match="Cannot find requested metafile"):
        read_metadata(out)


def test_config_stratigraphy_empty_entries_alias(globalconfig2, regsurf):
    """Test that empty entries in 'alias' is detected and warned and removed."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["alias"] += [None]

    exp = ExportData(config=cfg, content="depth", name="TopVolantis")
    metadata = exp.generate_metadata(regsurf)

    assert None not in metadata["data"]["alias"]


@pytest.mark.xfail(reason="stratigraphic_alias is not implemented")
def test_config_stratigraphy_empty_entries_stratigraphic_alias(globalconfig2, regsurf):
    """Test that empty entries in 'stratigraphic_alias' detected and warned."""

    # Note! stratigraphic_alias is not implemented, but we still check consistency

    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["stratigraphic_alias"] += [None]

    exp = ExportData(config=cfg, content="depth")
    metadata = exp.generate_metadata(regsurf)

    assert None not in metadata["data"]["stratigraphic_alias"]


def test_config_stratigraphy_empty_name(globalconfig2):
    """Test that empty 'name' is detected and warned."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["name"] = None

    with pytest.warns(UserWarning, match=pydantic_warning()):
        ExportData(config=cfg, content="depth")


def test_config_stratigraphy_stratigraphic_not_bool(globalconfig2):
    """Test that non-boolean 'stratigraphic' is detected and warned."""
    cfg = deepcopy(globalconfig2)
    cfg["stratigraphy"]["TopVolantis"]["stratigraphic"] = None

    with pytest.warns(UserWarning, match=pydantic_warning()):
        ExportData(config=cfg, content="depth")

    cfg["stratigraphy"]["TopVolantis"]["stratigraphic"] = "a string"

    with pytest.warns(UserWarning, match=pydantic_warning()):
        ExportData(config=cfg, content="depth")


def test_update_check_settings_shall_fail(globalconfig1):
    # pylint: disable=unexpected-keyword-arg
    with pytest.raises(TypeError):
        _ = ExportData(config=globalconfig1, stupid="str", content="depth")

    newsettings = {"invalidkey": "some"}
    some = ExportData(config=globalconfig1, content="depth")
    with pytest.raises(KeyError):
        some._update_check_settings(newsettings)


@pytest.mark.parametrize(
    "key, value, expected_msg",
    [
        (
            "runpath",
            "some",
            r"The 'runpath' key has currently no function",
        ),
        (
            "grid_model",
            "some",
            r"The 'grid_model' key has currently no function",
        ),
    ],
)
def test_deprecated_keys(globalconfig1, regsurf, key, value, expected_msg):
    """Some keys shall raise a DeprecationWarning or similar."""

    # under primary initialisation
    kval = {key: value}
    with pytest.warns(PendingDeprecationWarning, match=expected_msg):
        ExportData(config=globalconfig1, content="depth", **kval)

    # under override
    with pytest.warns(PendingDeprecationWarning, match=expected_msg):
        edata = ExportData(config=globalconfig1, content="depth")
        edata.generate_metadata(regsurf, **kval)


def test_content_not_given(globalconfig1, regsurf):
    """When content is not explicitly given, warning shall be issued."""
    with pytest.warns(UserWarning, match="The <content> is not provided"):
        eobj = ExportData(config=globalconfig1)
        mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["content"] == "unset"


def test_content_given_init_or_later(globalconfig1, regsurf):
    """When content is not explicitly given, warning shall be issued."""
    eobj = ExportData(config=globalconfig1, content="time")
    mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["content"] == "time"

    # override by adding content at generate_metadata
    mymeta = eobj.generate_metadata(regsurf, content="depth")

    assert mymeta["data"]["content"] == "depth"  # last content shall win


def test_content_invalid_string(globalconfig1):
    with pytest.raises(ValidationError):
        ExportData(config=globalconfig1, content="not_valid")


def test_content_invalid_dict(globalconfig1):
    with pytest.raises(ValidationError):
        ExportData(
            config=globalconfig1, content={"not_valid": {"some_key": "some_value"}}
        )


def test_content_valid_string(regsurf, globalconfig2):
    eobj = ExportData(config=globalconfig2, name="TopVolantis", content="seismic")
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "seismic"
    assert "seismic" not in mymeta["data"]


def test_content_valid_dict(regsurf, globalconfig2):
    """Test for incorrectly formatted dict.

    When a dict is given, there shall be one key which is the content, and there shall
    be one value, which shall be a dictionary containing content-specific attributes."""

    eobj = ExportData(
        config=globalconfig2,
        name="TopVolantis",
        content={
            "seismic": {
                "attribute": "amplitude",
                "calculation": "mean",
                "zrange": 12.0,
                "stacking_offset": "0-15",
            }
        },
    )
    mymeta = eobj.generate_metadata(regsurf)
    assert mymeta["data"]["content"] == "seismic"
    assert mymeta["data"]["seismic"] == {
        "attribute": "amplitude",
        "calculation": "mean",
        "zrange": 12.0,
        "stacking_offset": "0-15",
    }


def test_content_is_a_wrongly_formatted_dict(globalconfig2):
    """When content is a dict, it shall have one key with one dict as value."""
    with pytest.raises(ValueError, match="incorrectly formatted"):
        ExportData(
            config=globalconfig2,
            name="TopVolantis",
            content={"seismic": "myvalue"},
        )


def test_content_is_dict_with_wrong_types(globalconfig2):
    """When content is a dict, it shall have right types for known keys."""
    with pytest.raises(ValidationError):
        ExportData(
            config=globalconfig2,
            name="TopVolantis",
            content={
                "seismic": {
                    "stacking_offset": 123.4,  # not a string
                }
            },
        )


def test_content_with_subfields(globalconfig2, polygons):
    """When subfield is given and allowed, it shall be produced to metadata."""
    eobj = ExportData(
        config=globalconfig2,
        name="Central Horst",
        content={"field_region": {"id": 1}},
    )
    mymeta = eobj.generate_metadata(polygons)

    assert mymeta["data"]["name"] == "Central Horst"
    assert mymeta["data"]["content"] == "field_region"
    assert "field_region" in mymeta["data"]
    assert mymeta["data"]["field_region"] == {"id": 1}


def test_content_deprecated_seismic_offset(regsurf, globalconfig2):
    """Assert that usage of seismic.offset still works but give deprecation warning."""
    with pytest.warns(DeprecationWarning, match="seismic.offset is deprecated"):
        eobj = ExportData(
            config=globalconfig2,
            name="TopVolantis",
            content={
                "seismic": {
                    "offset": "0-15",
                }
            },
        )
        mymeta = eobj.generate_metadata(regsurf)

    # deprecated 'offset' replaced with 'stacking_offset'
    assert "offset" not in mymeta["data"]["seismic"]
    assert mymeta["data"]["seismic"] == {
        "stacking_offset": "0-15",
    }


def test_set_display_name(regsurf, globalconfig2):
    """Test that giving the display_name argument sets display.name."""
    eobj = ExportData(
        config=globalconfig2,
        name="MyName",
        display_name="MyDisplayName",
        content="depth",
    )
    mymeta = eobj.generate_metadata(regsurf)

    assert mymeta["data"]["name"] == "MyName"
    assert mymeta["display"]["name"] == "MyDisplayName"

    # also test when setting directly in the method call
    mymeta = eobj.generate_metadata(regsurf, display_name="MyOtherDisplayName")

    assert mymeta["data"]["name"] == "MyName"
    assert mymeta["display"]["name"] == "MyOtherDisplayName"


def test_global_config_from_env(monkeypatch, global_config2_path):
    """Testing getting global config from a file"""
    monkeypatch.setenv("FMU_GLOBAL_CONFIG", str(global_config2_path))
    edata = ExportData(content="depth")  # the env variable will override this
    assert "smda" in edata.config["masterdata"]


def test_norwegian_letters_globalconfig(
    globalvars_norwegian_letters,
    regsurf,
    monkeypatch,
):
    """Testing using norwegian letters in global config.

    Note that fmu.config utilities yaml_load() is applied to read cfg (cf conftest.py)
    """

    path, cfg, cfg_asfile = globalvars_norwegian_letters

    os.chdir(path)

    edata = ExportData(content="depth", config=cfg, name="TopBlåbær")
    meta = edata.generate_metadata(regsurf)
    logger.debug("\n %s", prettyprint_dict(meta))
    assert meta["data"]["name"] == "TopBlåbær"
    assert meta["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"

    # export to file and reread as raw
    result = pathlib.Path(edata.export(regsurf))
    metafile = result.parent / ("." + str(result.stem) + ".gri.yml")
    with open(metafile, encoding="utf-8") as stream:
        assert "DRÅGØN" in stream.read()

    # read file as global config

    monkeypatch.setenv("FMU_GLOBAL_CONFIG", cfg_asfile)
    edata2 = ExportData(content="depth")  # the env variable will override this
    meta2 = edata2.generate_metadata(regsurf, name="TopBlåbær")
    logger.debug("\n %s", prettyprint_dict(meta2))
    assert meta2["data"]["name"] == "TopBlåbær"
    assert meta2["masterdata"]["smda"]["field"][0]["identifier"] == "DRÅGØN"


def test_norwegian_letters_globalconfig_as_json(
    globalvars_norwegian_letters,
    regsurf,
):
    """Testing using norwegian letters in global config, with json output."""

    path, cfg, _ = globalvars_norwegian_letters
    os.chdir(path)

    ExportData.meta_format = "json"
    edata = ExportData(config=cfg, name="TopBlåbær", content="depth")

    result = pathlib.Path(edata.export(regsurf))
    metafile = result.parent / ("." + str(result.stem) + ".gri.json")
    with open(metafile, encoding="utf-8") as stream:
        assert "DRÅGØN" in stream.read()

    ExportData.meta_format = "yaml"  # reset


def test_establish_pwd_runpath(tmp_path, globalconfig2):
    """Testing pwd and rootpath from RMS"""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2, content="depth")
    edata._establish_pwd_rootpath()

    assert edata._rootpath == rmspath.parent.parent

    ExportData._inside_rms = False  # reset


@pytest.mark.skipif("win" in sys.platform, reason="Windows tests have no /tmp")
def test_forcefolder(tmp_path, globalconfig2, regsurf):
    """Testing the forcefolder mechanism."""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    edata = ExportData(config=globalconfig2, content="depth", forcefolder="whatever")
    with pytest.warns(UserWarning, match="The standard folder name is overrided"):
        meta = edata.generate_metadata(regsurf)
    logger.info("RMS PATH %s", rmspath)
    logger.info("\n %s", prettyprint_dict(meta))
    assert meta["file"]["relative_path"].startswith("share/results/whatever/")
    ExportData._inside_rms = False  # reset


@pytest.mark.skipif("win" in sys.platform, reason="Windows tests have no /tmp")
def test_forcefolder_absolute_shall_raise_or_warn(tmp_path, globalconfig2, regsurf):
    """Testing the forcefolder mechanism."""
    rmspath = tmp_path / "rms" / "model"
    rmspath.mkdir(parents=True, exist_ok=True)
    os.chdir(rmspath)

    ExportData._inside_rms = True
    ExportData.allow_forcefolder_absolute = False
    edata = ExportData(config=globalconfig2, content="depth", forcefolder="/tmp/what")
    with pytest.raises(ValueError):
        meta = edata.generate_metadata(regsurf, name="x")

    ExportData.allow_forcefolder_absolute = True
    edata = ExportData(config=globalconfig2, content="depth", forcefolder="/tmp/what")
    with pytest.warns(UserWarning, match="absolute paths in forcefolder is not rec"):
        meta = edata.generate_metadata(regsurf, name="y")

    assert (
        meta["file"]["relative_path"]
        == meta["file"]["absolute_path"]
        == "/tmp/what/y.gri"
    )
    ExportData.allow_forcefolder_absolute = False  # reset
    ExportData._inside_rms = False


def test_deprecated_verbosity(globalconfig1):
    with pytest.warns(UserWarning, match="Using the 'verbosity' key is now deprecated"):
        ExportData(config=globalconfig1, verbosity="INFO")


@pytest.mark.parametrize("encoding", ("utf-8", "latin1"))
@pytest.mark.parametrize("mode", ("w", "w+"))
def test_norwegian_letters(encoding, mode, tmp_path):
    with open(tmp_path / "no-letters.yml", encoding=encoding, mode=mode) as f:
        f.write(
            """æøå:
  æøå"""
        )

    with open(tmp_path / "no-letters.yml", encoding=encoding) as f:
        assert yaml.safe_load(f) == {"æøå": "æøå"}


@pytest.mark.parametrize("content", ("seismic", "property"))
def test_content_seismic_or_property_as_string_future_warning(content, globalconfig2):
    with pytest.warns(FutureWarning):
        ExportData(content=content, config=globalconfig2)


@pytest.mark.parametrize(
    "content",
    (
        {"seismic": {"attribute": "attribute-value"}},
        {"property": {"attribute": "attribute-value"}},
    ),
)
def test_content_seismic_or_property_as_composite_no_future_warning(
    content, globalconfig2, recwarn
):
    ExportData(content=content, config=globalconfig2)
    assert len(recwarn) == 0
