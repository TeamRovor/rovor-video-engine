"""Private Google Drive Desktop delivery of verified Evan review MP4s.

Requires the user to sign into Google Drive for desktop on this Mac first.
Never sends private media to GitHub Actions artifacts or public URLs.
A local file copy is NOT proof that cloud synchronization has finished.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HOME=Path.home()
SOURCE=HOME/"Desktop/ROVOR_Evan_Full_Verified"
STEMS=("Landscape", "Portrait")
FORMATS={"Landscape": (1920,1080), "Portrait": (1080,1920)}
FOLDER="Rovor Video Reviews"


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def verified_sources():
    files=[]
    for name in STEMS:
        video=SOURCE/f"Evan_Verified_Development_1080p60_{name}.mp4"
        report=SOURCE/f"final-{'landscape' if name == 'Landscape' else 'portrait'}.json"
        if not video.is_file() or not report.is_file():
            raise ValueError(f"{name}: missing finished video or decoded verification report")
        record=json.loads(report.read_text())
        if record.get("videoSha256")!=sha256(video):
            raise ValueError(f"{name}: decoded verifier SHA mismatch")
        if tuple(record.get("dimensions",[]))!=FORMATS[name]:
            raise ValueError(f"{name}: incorrect frame dimensions")
        if record.get("fps")!=60 or not record.get("continuousTimestamps"):
            raise ValueError(f"{name}: invalid frame timing")
        if record.get("decodedFrames")!=1323:
            raise ValueError(f"{name}: this delivery handles the 22-second verified reference only")
        if abs(record.get("offsetSamples",99999))>32 or record.get("referenceCorrelation",0)<.98:
            raise ValueError(f"{name}: audio alignment was not verified")
        files.extend((video,report))
    return files


def find_drive_mount():
    folders=list((HOME/"Library/CloudStorage").glob("GoogleDrive*"))
    folders+=list(Path("/Volumes").glob("GoogleDrive*"))
    for drive in folders:
        for part in ("My Drive","MyDrive",""):
            root=drive/part
            # Google Drive for Desktop exposes the signed-in My Drive folder here.
            if root.is_dir() and (root/"shortsrovordigital").is_dir():
                return root
    raise RuntimeError("Google Drive for Desktop not signed in to the narration account; no media copied")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label",default="Evan-22-second-verified")
    args=ap.parse_args()
    label=args.label
    if len(label)>50 or not all(c.isalnum() or c in "-_" for c in label):
        ap.error("Invalid output label")
    files=verified_sources()
    dest=find_drive_mount()/FOLDER/label
    if dest.exists():
        raise FileExistsError("Review destination already exists; do not overwrite previous review")
    dest.mkdir(parents=True,exist_ok=False)
    for file in files:
        shutil.copy2(file,dest/file.name)
        if sha256(file)!=sha256(dest/file.name):
            raise IOError("Copied file checksum differs: "+file.name)
    (dest/"DELIVERY_STATUS.json").write_text(json.dumps({
        "status":"COPIED_TO_GOOGLE_DRIVE_DESKTOP_SYNC_FOLDER",
        "cloudSyncVerified":False,
        "publicationApproved":False,
        "files":[{"name":p.name,"sha256":sha256(p)} for p in files],
        "note":"Confirm upload completion in Google Drive separately before sharing."
    },indent=2)+"\n")
    print("PRIVATE_DELIVERY_LOCAL_COPY=COMPLETE")
    print("CLOUD_SYNC_VERIFIED=NO")
    print("OUTPUT_DRIVE_FOLDER="+str(dest))


if __name__=="__main__":
    main()
