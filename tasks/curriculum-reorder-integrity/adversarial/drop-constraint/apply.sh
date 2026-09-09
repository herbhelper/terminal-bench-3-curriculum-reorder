#!/bin/bash
# Apply adversarial variant: drop-constraint
set -e
/app/curriculum/scripts/dbup.sh
cp /solution/fixed/importer.py /app/curriculum/curriculum/importer.py
cp /adversarial/drop-constraint/ordering.py /app/curriculum/curriculum/ordering.py
echo "applied drop-constraint"
