#!/bin/sh
set -e
# The examples scripts are ran and included in the documentation!

current=$PWD

# empty current results
rm -fr examples/s/d/nn/xcase/realization-0/iter-0/share/results/*


cd $current/examples/s/d/nn/xcase/realization-0/iter-0/rms/bin/
python export_faultpolygons.py
python export_propmaps.py

cd $current/examples/s/d/nn/xcase/realization-0/iter-0/any/bin/
python export_grid3d.py
python export_volumetables.py

cd $current
