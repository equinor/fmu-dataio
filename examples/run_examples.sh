#!/bin/sh
set -e

#===================================================================================
#
# FILE: run_example.sh
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

#--------- Empty current results and metadata ---------#
echo "Remove former output..."
rm -rf $examples_rootpath/realization-*/iter-0/share/results/*
rm -rf $examples_rootpath/iter-0/*
rm -rf $examples_rootpath/share/preprocessed
rm -rf $examples_rootpath/share/metadata/fmu_case.yml


#--------- Create a new fmu case up to date with the latest case model ---------#
cd $examples_rootpath
python scripts/export_fmu_case.py


#--------- Export files and metadata ---------#

# fake an ERT FMU run
cd $examples_rootpath/realization-0/iter-0/scripts
export _ERT_EXPERIMENT_ID=6a8e1e0f-9315-46bb-9648-8de87151f4c7
export _ERT_ENSEMBLE_ID=b027f225-c45d-477d-8f33-73695217ba14
export _ERT_SIMULATION_MODE=test_run
export _ERT_ITERATION_NUMBER=0
export _ERT_REALIZATION_NUMBER=0
export _ERT_RUNPATH=$examples_rootpath/realization-0/iter-0

python export_polygons.py
python export_propmaps.py
python export_faultroom_surfaces.py
python export_preprocessed_surface.py
python export_grid3d.py
python export_volumetables.py
python export_surface_maps.py


#--------- Export aggregated surfaces (to be used in unit tests) ---------#

echo "Exporting files and metadata for two additinal realizations to be able to do aggregation."
for num in 1 9; do
    cd $examples_rootpath/realization-${num}/iter-0/scripts
    echo "Running simple surface export for realization $num..."
    
    export _ERT_REALIZATION_NUMBER=$num
    export _ERT_RUNPATH=$examples_rootpath/realization-${num}/iter-0
    
    python export_surface_maps.py
done

# Aggregate the surfaces exported from all realizations.
cd $examples_rootpath/scripts
python aggregate_surfaces.py

#--------- Update schema metadata with the newly exported metadata ---------#
cd $examples_rootpath
echo "Updating schema metadata..."

# Update surface metadata
cp $examples_rootpath/realization-0/iter-0/share/results/maps/.topvolantis--ds_extract_geogrid.gri.yml share/metadata/surface_depth.yml
cp $examples_rootpath/realization-0/iter-0/share/results/maps/.surface_fluid_contact.gri.yml share/metadata/surface_fluid_contact.yml
cp $examples_rootpath/realization-0/iter-0/share/results/maps/.surface_seismic_amplitude--20201028_20201028.gri.yml share/metadata/surface_seismic_amplitude.yml

# Update preprocessed metadata
cp $examples_rootpath/share/preprocessed/maps/mysub/.preprocessedmap.gri.yml share/metadata/preprocessed_surface_depth.yml

# Update volume table metadata
cp $examples_rootpath/realization-0/iter-0/share/results/tables/.geogrid--volumes.csv.yml share/metadata/table_inplace_volumes.yml

# Update polygon metadata
cp $examples_rootpath/realization-0/iter-0/share/results/polygons/.volantis_gp_base--polygons_field_region.csv.yml share/metadata/polygons_field_region.yml
cp $examples_rootpath/realization-0/iter-0/share/results/polygons/.volantis_gp_base--polgons_field_outline.csv.yml share/metadata/polygons_field_outline.yml

# Update aggregation metadata
cp $examples_rootpath/iter-0/share/results/maps/.aggregated_surfaces.gri.yml share/metadata/aggregated_surface_depth.yml

echo "Done updating schema metadata."