from __future__ import annotations

import warnings

from fmu.dataio._models.fmu_results.global_configuration import Stratigraphy


class Utils:
    @staticmethod
    def get_stratigraphic_name(stratigraphy: Stratigraphy, name: str) -> str:
        """
        Get the name of a stratigraphic element from the stratigraphy.
        name: name of stratigraphic element
        """
        if name in stratigraphy:
            return stratigraphy[name].name

        warnings.warn(
            f"Stratigraphic element '{name}' not found in the stratigraphic column "
            "in global config"
        )
        return ""
