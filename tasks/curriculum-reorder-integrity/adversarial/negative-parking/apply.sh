#!/bin/bash
# Apply adversarial variant: negative-parking
set -e
/app/curriculum/scripts/dbup.sh
cp /solution/fixed/importer.py /app/curriculum/curriculum/importer.py
cp /adversarial/negative-parking/ordering.py /app/curriculum/curriculum/ordering.py
echo "applied negative-parking"
