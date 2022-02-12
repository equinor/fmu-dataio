#!/bin/sh
set -e
# The examples scripts are ran and included in the documentation!

export RUN_DATAIO_EXAMPLES=1  # this is important when running examples!

current=$PWD

# empty current results
echo "Remove former output..."
rm -fr examples/s/d/nn/xcase/realization-0/iter-0/share/results/*

# Note! run from RUNPATH, NOT being inside RMS but need RUN_DATAIO_EXAMPLES env!
cd $current/examples/s/d/nn/xcase/realization-0/iter-0/rms/bin

python export_faultpolygons.py
python export_propmaps.py

cd $current/examples/s/d/nn/xcase/realization-0/iter-0/any/bin

python export_grid3d.py
python export_volumetables.py

for num in 0 1 9; do
    cd $current/examples/s/d/nn/xcase/realization-${num}/iter-0/rms/bin
    python export_a_surface.py
done


cd $current
