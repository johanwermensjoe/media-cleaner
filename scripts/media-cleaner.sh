#!/bin/sh
configFilePath=$1
pythonPath=/usr/lib/media-cleaner/

# Cleanup and sort.
echo "Running cleanup: $(date)"
echo "------------------------------------------------"
echo ""
python ${pythonPath}media_cleaner.py -vtm "${configFilePath}"
echo "------------------------------------------------"
echo ""
