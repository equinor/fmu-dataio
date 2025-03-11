## Examples
This folder contains scripts, config and input data to generate the examples used to demonstrate
how `fmu-dataio` can be used for different contexts, and for different data types.

In addition, you will also find examples of metadata that `fmu-dataio` produces under the
`/share/metadata` folder. These files are used by the unit tests to test the Pydantic logic.

### Folders and files
If you study the folder structure under `/examples`, you will see that there are three realizations folders:
* Most of the logic and data exports are done by the scripts in `realization-0`.
* The two other realizations, `realization-1` and `realization-9` are only there to export some simple
surfaces needed in order to be able to run aggregations.

The `/script` folder located at the `/examples` root contains scripts that are not related to any
specific realizations:
* `export_fmu_case.py`: A script that creates a new fmu case based on the current schema version.
* `aggregate_surfaces.py`: A script that runs aggregations over the surfaces exported by the three realizations.

### Running the scripts
The bash script `run_examples.sh` runs all the python export scripts in the correct order and exports files
and metadata to its right location so that they can be accessed by the documentation and test files. The 
`run_examples.sh` script will mainly be run by other processes to make sure files and metadata are up to date.
If you run it manually, make sure to run it from the root folder of the `fmu-dataio` project. Example:
* `cd path/to/root/of/fmu-dataio/project`
* `bash ./examples/run_examples.sh`