from __future__ import annotations

from ert import plugin
from ert.plugins.plugin_manager import hook_implementation


@hook_implementation
@plugin(name="fmu_dataio")
def installable_workflow_jobs() -> dict:
    return {}
