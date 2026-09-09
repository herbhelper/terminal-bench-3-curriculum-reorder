# curriculum

The ordering service behind a course curriculum: sections hold lessons, and a
lesson's place in its section is dense, 1-based, and enforced by the database.

```bash
scripts/dbup.sh                 # start postgres, create the database
python -m curriculum.seed       # build the sample curriculum
python -m pytest tests -q       # the shipped suite
```

Layout:

- `curriculum/schema.sql` — tables, the deferrable uniqueness constraint, the move audit trigger
- `curriculum/ordering.py` — appending, moving and renumbering lessons
- `curriculum/importer.py` — bulk import from the legacy export
- `curriculum/seed.py` — the sample curriculum
