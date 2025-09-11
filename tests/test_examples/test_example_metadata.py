from copy import deepcopy

import pytest
from fmu.datamodels.fmu_results.fmu_results import FmuResults
from pydantic import ValidationError

from tests.utils import _metadata_examples


@pytest.mark.parametrize("file, example", _metadata_examples().items())
def test_schema_example_filenames(file, example):
    """Assert that all examples are .yml, not .yaml"""
    assert file.endswith(".yml")


@pytest.mark.parametrize("file, example", _metadata_examples().items())
def test_validate(file, example):
    """Confirm that examples are valid against the schema"""
    FmuResults.model_validate(example)


def test_sumo_ensemble(metadata_examples):
    """Asserting validation failure when illegal contents in ensemble metadata"""

    example = metadata_examples["sumo_ensemble.yml"]

    # assert validation with no changes
    FmuResults.model_validate(example)

    # assert validation error when "fmu" is missing
    _example = deepcopy(example)
    del _example["fmu"]

    with pytest.raises(ValidationError):
        FmuResults.model_validate(_example)

    # assert validation error when "fmu.ensemble" is missing
    _example = deepcopy(example)
    del _example["fmu"]["ensemble"]

    with pytest.raises(ValidationError):
        FmuResults.model_validate(_example)

    # assert validation error when "fmu.context.stage" is not ensemble
    _example = deepcopy(example)
    _example["fmu"]["context"]["stage"] = "case"

    with pytest.raises(ValidationError):
        FmuResults.model_validate(_example)


def test_sumo_realization(metadata_examples):
    """Asserting validation failure when illegal contents in realization example"""

    example = metadata_examples["sumo_realization.yml"]

    # assert validation with no changes
    FmuResults.model_validate(example)

    # assert validation error when "fmu" is missing
    _example = deepcopy(example)
    del _example["fmu"]

    with pytest.raises(ValidationError):
        FmuResults.model_validate(_example)

    # assert validation error when "fmu.realization" is missing
    _example = deepcopy(example)
    del _example["fmu"]["realization"]

    with pytest.raises(ValidationError):
        FmuResults.model_validate(_example)

    # assert validation error when "fmu.context.stage" is not realization
    _example = deepcopy(example)
    _example["fmu"]["context"]["stage"] = "iteration"

    with pytest.raises(ValidationError):
        FmuResults.model_validate(_example)


def test_fmu_iteration_set_from_fmu_ensemble(metadata_examples):
    """Test that fmu.iteration is set from the fmu.ensemble."""

    # fetch example
    example = metadata_examples["surface_depth.yml"]

    # assert validation with no changes
    FmuResults.model_validate(example)

    assert "iteration" in example["fmu"]
    assert "ensemble" in example["fmu"]

    # delete fmu.iteration and see that is set from the fmu.ensemble
    _example = deepcopy(example)
    del _example["fmu"]["iteration"]
    _example["fmu"]["ensemble"]["name"] = "pytest"

    model = FmuResults.model_validate(_example)

    assert hasattr(model.root.fmu, "iteration")
    assert model.root.fmu.iteration == model.root.fmu.ensemble
    assert model.root.fmu.iteration.name == "pytest"
