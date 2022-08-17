try:
    import ert_shared
except ModuleNotFoundError:
    import ert.shared as ert_shared


@ert_shared.plugins.plugin_manager.hook_implementation
@ert_shared.plugins.plugin_manager.plugin_response(plugin_name="fmu_dataio")
def installable_workflow_jobs():
    return {}
