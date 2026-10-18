"""Fail-closed promotion of BOTH completed Rovor video orientations.

The full exports are first verified independently, including every frame and
distributed original narration. Never overwrite previously accepted videos
unless *both* newly encoded outputs pass. This is a technical gate only.
"""
import hashlib
import json
from pathlib import Path
from verify_longform_export import verify

REAL_SIZES={"landscape":(1920,1080),"vertical":(1080,1920)}


def promote(pairs,ffmpeg,wav,start_frame,end_frame,output_dir,source_hash,
            sizes=REAL_SIZES):
    """Atomically replace each destination only AFTER both sources validate.

    A report is committed only when both completed exports are in place.
    Test canvases may supply explicit small sizes; production must use
    REAL_SIZES and preserve all previous exports if verification rejects.
    """
    output_dir=Path(output_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    if not isinstance(pairs,list) or len(pairs)!=2:
        raise ValueError("Both landscape and portrait output candidates required")
    originals={}
    for name,temp,dest in pairs:
        if name not in ("landscape","vertical") or name in originals:
            raise ValueError("Invalid/duplicated original Evan output orientation")
        temp,dest=Path(temp),Path(dest)
        if temp.is_symlink() or dest.is_symlink():
            raise ValueError("Media symlinks rejected")
        if temp.parent.resolve()!=output_dir or dest.parent.resolve()!=output_dir:
            raise ValueError("Do not write media outside the isolated review directory")
        originals[name]=(temp,dest)
    if set(originals)!=set(REAL_SIZES):
        raise ValueError("Landscape and portrait must both exist")
    if not isinstance(source_hash,str) or len(source_hash)!=64 or any(
            ch not in "0123456789abcdef" for ch in source_hash):
        raise ValueError("Original audio source checksum missing")

    results={}
    for name in ("landscape","vertical"):
        temp,dest=originals[name]
        size=sizes[name]
        result=verify(ffmpeg,temp,wav,size=size,start_frame=start_frame,
                      end_frame=end_frame)
        if result["voiceWindowsVerified"]<3:
            raise ValueError("Insufficient source voice evidence in "+name)
        results[name]=result
    if results["landscape"]["decodedFrames"]!=results["vertical"]["decodedFrames"]:
        raise ValueError("Landscape and portrait do not share the same original audio frames")
    if results["landscape"]["selectedStartFrame"]!=results["vertical"]["selectedStartFrame"]:
        raise ValueError("The two videos refer to different narration starts")
    if results["landscape"]["selectedEndFrameExclusive"]!=results["vertical"]["selectedEndFrameExclusive"]:
        raise ValueError("The two videos refer to different narration ends")

    report={
        "status":"TWO_FORMAT_RENDERED_MEDIA_TECHNICALLY_VERIFIED",
        "fps":60,"sourceAudioHash":source_hash,
        "landscape":results["landscape"],"portrait":results["vertical"],
        "phonemeTimingArtistCertified":False,"studioVisualQualityApproved":False,
        "publicationApproved":False
    }
    # Do not write the final marker until both successfully verified files
    # have been moved into place. Incomplete restarts must re-run checks.
    report_path=output_dir/"final-media-integrity.json"
    report_tmp=output_dir/"final-media-integrity.partial.json"
    if report_tmp.is_symlink() or report_path.is_symlink():
        raise ValueError("Invalid integrity report paths")
    report_tmp.write_text(json.dumps(report,indent=2)+"\n")
    for name in ("landscape","vertical"):
        temp,dest=originals[name]
        temp.replace(dest)
    report_tmp.replace(report_path)
    return report
