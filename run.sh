#!/bin/bash
# Activate conda environment
source /opt/anaconda3/bin/activate youtube-shorts

# Fix OpenMP duplicate library issue on macOS
export KMP_DUPLICATE_LIB_OK=TRUE

python main.py "$@"

