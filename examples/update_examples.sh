#!/bin/sh
set -e

#===================================================================================
#
# FILE: update_examples.sh
#
# USAGE: To be run by /tools/update-schema and by CI when updating documentation
#
# DESCRIPTION: Generates files and metadata to be used
#   1) As examples in the documentation on how to use fmu-dataio to export data
#   2) For unit testing the versioned schema metadata of fmu-dataio
# 
# NB! Run this script from the project root if run manually
#
#===================================================================================

current=$PWD
examples_rootpath=$current/examples


#--------- Remove old exported results and metadata ---------#
echo "Remove old exported results and metadata..."
rm -rf $examples_rootpath/example_exports/.dataio_export_manifest.json
rm -rf $examples_rootpath/example_exports/share
rm -rf $examples_rootpath/share
rm -rf $examples_rootpath/example_metadata/metadata_scripts/share/metadata/fmu_case.yml


#--------- Create a new fmu case metadata up to date with the latest case model ---------#
cd $examples_rootpath
python metadata_scripts/create_case_metadata.py


#--------- Export files and metadata using the example export scripts ---------#

# fake an ERT FMU run
export _ERT_EXPERIMENT_ID=00000000-0000-0000-0000-000000000000
export _ERT_ENSEMBLE_ID=b027f225-c45d-477d-8f33-73695217ba14
export _ERT_SIMULATION_MODE=test_run
export _ERT_RUNPATH=$examples_rootpath/example_exports

# Run examples for exporting RMS data
cd $examples_rootpath/example_exports/export_rms_data
python export_faultpolygons.py
python export_polygons.py
python export_propmaps.py
python export_faultroom_surfaces.py
python export_preprocessed_surface.py
python export_surface_maps.py

# Run examples for exporting non-RMS data
cd $examples_rootpath/example_exports/export_non_rms_data
python export_grid3d.py
python export_volumetables.py


#--------- Create aggregation metadata (to be used in unit tests) ---------#

# The scripts will emulate an aggregation of a surface across 3 realizations
cd $examples_rootpath/metadata_scripts
python create_aggregation_metadata.py


#--------- Update the metadata examples with the newly created metadata ---------#
cd $examples_rootpath

echo "Updating schema metadata..."

# Update fmu case
cp $examples_rootpath/share/metadata/fmu_case.yml example_metadata/fmu_case.yml 

# Update surface metadata
cp $examples_rootpath/example_exports/share/results/maps/.topvolantis--ds_extract_geogrid.gri.yml example_metadata/surface_depth.yml
cp $examples_rootpath/example_exports/share/results/maps/.surface_fluid_contact.gri.yml example_metadata/surface_fluid_contact.yml
cp $examples_rootpath/example_exports/share/results/maps/.surface_seismic_amplitude--20201028_20201028.gri.yml example_metadata/surface_seismic_amplitude.yml

# Update preprocessed metadata
cp $examples_rootpath/share/preprocessed/maps/mysub/.preprocessedmap.gri.yml example_metadata/preprocessed_surface_depth.yml

# Update volume table metadata
cp $examples_rootpath/example_exports/share/results/tables/.geogrid--volumes.csv.yml example_metadata/table_inplace_volumes.yml

# Update polygon metadata
cp $examples_rootpath/example_exports/share/results/polygons/.volantis_gp_base--polygons_field_region.csv.yml example_metadata/polygons_field_region.yml
cp $examples_rootpath/example_exports/share/results/polygons/.volantis_gp_base--polygons_field_outline.csv.yml example_metadata/polygons_field_outline.yml

# Update grid and grid property metadata 
cp $examples_rootpath/example_exports/share/results/grids/.geogrid.roff.yml example_metadata/geogrid.yml
cp $examples_rootpath/example_exports/share/results/grids/.geogrid--phit.roff.yml example_metadata/geogrid--phit.yml
cp $examples_rootpath/example_exports/share/results/grids/.geogrid--facies.roff.yml example_metadata/geogrid--facies.yml

#Update aggregation metadata
cp $examples_rootpath/share/results/maps/.aggregated_surfaces.gri.yml share/metadata/aggregated_surface_depth.yml

echo "Done updating schema metadata."


#--------- Remove machine specific details from metadata files ---------#
cd $examples_rootpath/metadata_scripts
python post_process_metadata.py
