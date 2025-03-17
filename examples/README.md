## Examples
This folder contains scripts, config and input data to generate the examples
used to demonstrate how `fmu-dataio` can be used for different contexts.

In addition, you will also find examples of metadata that `fmu-dataio` produces
under the `/example_metadata` folder. These files are used by the unit tests
to test the Pydantic logic.

### Subfolders and files
Brief explanation of the subfolders and their purpose:
* `/example_exports`: Contains code examples of how you can use `fmu-dataio` to
export files and metadata, both for RMS and non-RMS data.
* `/fmuconfig`: Contains the global variables file used in the example exports.
* `/example_metadata`: Contains examples of metadata exported by `fmu-dataio`.
These files are used by the unit tests to test the Pydantic logic.
* `/metadata_scripts`: Contains scripts used to create and process metadata 
files, a dependency for the `update_examples.sh` script.
* `/archived_examples`: Contains export examples that are no longer used in the
documentation or tests, but that might still be useful to keep as examples.

#### The script `update_examples.sh`
* Runs all the example export scripts in the correct order and uses the exported
data to update the files and metadata referenced in the documentation and test
files. In this way the example files and metadata will always be up to date with
the latest models and schema version.
* The script will mainly be run by other processes to make sure
files and metadata are up to date:
    * The schema update script `update-schemas` runs `update_examples.sh` to update
    the metadata examples so that they are in sync with the updated schema.
    * The documentation builder runs `update_examples.sh` to update the metadata
    and files that are referenced in the example documentation.
* NB! If you run the script manually, make sure to run it from the root folder
of the `fmu-dataio` project.