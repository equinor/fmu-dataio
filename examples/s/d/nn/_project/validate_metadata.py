"""Example usage of the validation method.

Metadata produced by FMU adheres to the JSON schema. Outgoing data are associated with
metadata, which is validated in many different contexts.

The embedded validation script in fmu-dataio enables validation directly, which is
useful particularly in debugging situations.

This is an example of how this script is used.
"""

from pathlib import Path

from fmu.dataio import validate_metadata


def main():

    mycase = Path("../xcase/")
    myreal = "realization-0"
    myiter = "iter-0"
    mydatapath = "share/results/maps/topvolantis--ds_extract_geogrid.gri"

    # validate one
    one_path = Path(mycase / myreal / myiter / mydatapath)

    validate_metadata(one_path)

    # validate many
    reals = [0, 1, 9]
    many_paths = [
        mycase / f"realization-{real}" / myiter / mydatapath for real in reals
    ]

    validate_metadata(many_paths)


if __name__ == "__main__":
    main()
