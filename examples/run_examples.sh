#!/bin/sh
set -e
# The examples scripts are ran and included in the documentation!

current=$PWD

# empty current results
echo "Remove former output..."
rm -rf examples/s/d/nn/xcase/realization-*/iter-0/share/results/*
rm -rf examples/s/d/nn/xcase/iter-0/*

# Note! run from RUNPATH, NOT being inside RMS but need RUN_DATAIO_EXAMPLES env!
cd $current/examples/s/d/nn/xcase/realization-0/iter-0/rms/bin

# fake an ERT FMU run
export _ERT_EXPERIMENT_ID=6a8e1e0f-9315-46bb-9648-8de87151f4c7
export _ERT_ENSEMBLE_ID=b027f225-c45d-477d-8f33-73695217ba14
export _ERT_SIMULATION_MODE=test_run
export _ERT_ITERATION_NUMBER=0
export _ERT_REALIZATION_NUMBER=0
export _ERT_RUNPATH=$current/examples/s/d/nn/xcase/realization-0/iter-0

python export_faultpolygons.py
python export_propmaps.py
python export_faultroom_surfaces.py

cd $current/examples/s/d/nn/xcase/realization-0/iter-0/any/bin

python export_grid3d.py
python export_volumetables.py

# Emulate FMU run with 3 realizations and export data to disk
for num in 0 1 9; do
    cd $current/examples/s/d/nn/xcase/realization-${num}/iter-0/rms/bin

    export _ERT_REALIZATION_NUMBER=$num
    export _ERT_RUNPATH=${current}/examples/s/d/nn/xcase/realization-${num}/iter-0

    python export_a_surface.py
done

# Run the aggregation post-process
cd $current/examples/s/d/nn/_project
python aggregate_surfaces.py

cd $current
