#!/bin/bash
# Apply adversarial variant: delete-reinsert
set -e
/app/curriculum/scripts/dbup.sh
cp /solution/fixed/importer.py /app/curriculum/curriculum/importer.py
cp /adversarial/delete-reinsert/ordering.py /app/curriculum/curriculum/ordering.py
echo "applied delete-reinsert"
