try:
    from ert_shared.plugins.plugin_manager import hook_implementation, plugin_response  # type: ignore
except ModuleNotFoundError:
    from ert.shared.plugins.plugin_manager import hook_implementation, plugin_response # type: ignore


@ert_shared.plugins.plugin_manager.hook_implementation
@ert_shared.plugins.plugin_manager.plugin_response(plugin_name="fmu_dataio")
def installable_workflow_jobs():
    return {}
