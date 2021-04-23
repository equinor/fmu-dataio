Examples
========

Exporting surfaces in RMS Python (tentative)
--------------------------------------------

.. code-block:: python

    import xtgeo
    from fmu.config import utilities as ut
    from fmu.dataio import ExportData

    PRJ = project

    # load fmuconfig global variables
    CFG = ut.yaml_load("../../fmuconfig/output/global_variables.yml")

    HNAMES = ["TopValysar", "TopVolon"]
    DCATEGORIES = ["DS_extract_hum", "DS_interp"]
    TCATEGORIES = ["TS_interp", "TS_inverted"]

    CLIPFOLDER = "Volume/example"
    CLIPNAMES = ["STOOIP", "HCPV"]

    # set my default format for surfaces to irap_binary since HDF is builtin default
    ExportData.surface_fformat = "irap_binary"   # class attribute


    def export_depth_horizons():
        """Export horizons with 'depth' as content/scope."""

        dexp = ExportData(project=PRJ, content="depth", config=CFG)

        # export depth surfaces
        for cat in DCATEGORIES:
            for hname in HNAMES:
                surf = xtgeo.surface_from_roxar(PRJ, hname, cat, stype="horizons")
                exp.to_file(surf)


    def export_time_horizons():
        """Export horizons with 'time' as content/scope."""

        texp = ExportData(project=PRJ, content="time", config=CFG)

        for cat in TCATEGORIES:
            for hname in HNAMES:
                surf = xtgeo.surface_from_roxar(PRJ, hname, cat, stype="horizons")
                exp.to_file(surf)


    def export_volumetric_maps():
        """Export horizons with 'volume' as content/scope."""

        vexp = ExportData(project=PRJ, content="volume", config=CFG)

        for cname in CLIPNAMES:
            surf = xtgeo.surface_from_roxar(PRJ, cname, CLIPFOLDER, stype="clipboard")
            vexp.to_file(surf)


    if __name__ == "__main__":
        export_depth_horizons()
        export_time_horizons()
        export_volumetric_maps()
