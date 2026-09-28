#!/bin/bash

echo "======================================"
echo "      PARROT STARTUP SCRIPT"
echo "======================================"

cd /home/parrot

if [ -x /home/parrot/bootstrap.sh ]; then
    /home/parrot/bootstrap.sh >> /home/parrot/startup.log 2>&1
else
    echo "ERROR: /home/parrot/bootstrap.sh not found" >> /home/parrot/startup.log
    exit 1
fi
