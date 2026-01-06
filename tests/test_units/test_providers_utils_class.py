import pytest

from fmu.dataio.dataio import ExportData
from fmu.dataio.providers.objectdata._utils import Utils


def test_stratigraphy(edataobj2: ExportData) -> None:
    """Test the stratigraphy."""

    strat = edataobj2.config.stratigraphy

    ###### Test get stratigraphic name ######

    # Correct name
    assert Utils.get_stratigraphic_name(strat, "Valysar") == "Valysar Fm."

    # Incorrect name
    with pytest.warns(UserWarning, match="not found in the stratigraphic column"):
        assert Utils.get_stratigraphic_name(strat, "Ile") == ""

    # Empty name
    with pytest.warns(UserWarning, match="not found in the stratigraphic column"):
        assert Utils.get_stratigraphic_name(strat, "") == ""
