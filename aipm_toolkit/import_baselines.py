import argparse
import json
from pathlib import Path

from .baseline_services import (
    import_legacy_reference_json,
    preview_legacy_reference_json,
    publish_all_reference_datasets,
)
from .db import Base, SessionLocal, engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Import instructor reference JSON files")
    parser.add_argument("directory")
    parser.add_argument("--cohort", default="Legacy instructor reference")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--manifest")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8")) if args.manifest else None
    if args.preview:
        print(preview_legacy_reference_json(args.directory, manifest))
        return
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        report = import_legacy_reference_json(db, args.directory, args.cohort, manifest)
        if args.publish:
            publish_all_reference_datasets(db, args.cohort)
    print(report)


if __name__ == "__main__":
    main()
