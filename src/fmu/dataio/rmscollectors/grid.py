import logging
from dataclasses import dataclass
from fmu.dataio.rmscollectors import utils


@dataclass
class RmsGrid:
    """Class for exporting data Grid"""

    project: str
    grid_name: str
    job_name: str
    params: dict = None

    def __post_init__(self):
        """Initialize what is not initialized upfront"""
        self.params = utils.get_job_arguments(
            ["Grid models", self.grid_name, "Grid"], "Create Grid", self.job_name
        )
        self.project = utils._get_project(self.project, True)
