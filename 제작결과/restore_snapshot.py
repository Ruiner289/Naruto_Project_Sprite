"""Restore the complete generated sprite snapshot (Python 3, stdlib only)."""
from pathlib import Path
import argparse, hashlib, json, shutil, zipfile

def digest(file):
    h = hashlib.sha256()
    with file.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()

def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=here / "restored")
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("Destination must be empty: " + str(target))
    meta = json.loads((here / "backup" / "manifest.json").read_text(encoding="utf-8"))
    archive = here / "snapshot-restored.zip"
    with archive.open("wb") as output:
        for item in meta["parts"]:
            part = here / "backup" / item["file"]
            if part.stat().st_size != item["bytes"] or digest(part) != item["sha256"]:
                raise RuntimeError("Part checksum mismatch: " + item["file"])
            with part.open("rb") as stream:
                shutil.copyfileobj(stream, output)
    if archive.stat().st_size != meta["bytes"] or digest(archive) != meta["sha256"]:
        raise RuntimeError("Archive checksum mismatch")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            candidate = (target / item.filename).resolve()
            if not candidate.is_relative_to(target):
                raise RuntimeError("Unsafe archive path: " + item.filename)
        z.extractall(target)
    inventory = json.loads((target / "FILE_INVENTORY.json").read_text(encoding="utf-8"))
    for item in inventory["files"]:
        file = target / item["path"]
        if file.stat().st_size != item["bytes"] or digest(file) != item["sha256"]:
            raise RuntimeError("Restored checksum mismatch: " + item["path"])
    print("Restored and verified", len(inventory["files"]), "files plus inventory.")
    print(target)

if __name__ == "__main__":
    main()
