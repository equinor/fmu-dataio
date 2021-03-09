Examples
========

Exporting surfaces in RMS Python
--------------------------------

.. code-block:: python

    from fmu.config import utilities as ut
    from fmu.dataio import ExportFromRMS

    CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

    META_DEPTH = CFG["global"]["something"]

    EXP = ExportFromRMS(project)

    NAMES = ["TopValysar", "TopVolon"]

    def export_horizons():
        EXP.to_file(names=NAMES, category="DS_interp", metadata=META)

    if __name__ == "__main__":
        export_horizons()
        