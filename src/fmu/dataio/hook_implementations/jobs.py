try:
    from ert_shared.plugins.plugin_manager import hook_implementation, plugin_response
except ModuleNotFoundError:
    from ert.shared.plugins.plugin_manager import hook_implementation, plugin_response


@hook_implementation
@plugin_response(plugin_name="fmu_dataio")
def installable_workflow_jobs():
    return {}
