#!/bin/bash
# Apply adversarial variant: fix-the-reported-case
set -e
/app/curriculum/scripts/dbup.sh
cp /solution/fixed/importer.py /app/curriculum/curriculum/importer.py
cp /adversarial/fix-the-reported-case/ordering.py /app/curriculum/curriculum/ordering.py
echo "applied fix-the-reported-case"
