"""Verify a local H.264 render chunk before accepting it for a resumed job.

This is a structural gate (dimensions, cadence and full decodability), not a
substitute for the final FFmpeg timestamp/audio verifier or artistic review.
"""
from pathlib import Path
import cv2


def chunk_matches(path, expected_frames, size, fps):
    """Return True only when every expected frame can be decoded.

    Re-encode on any error rather than silently reusing a truncated chunk.
    The final review verifier separately checks exact PTS and voice integrity.
    """
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        return False
    if not isinstance(expected_frames, int) or expected_frames < 1:
        raise ValueError('Expected frames must be a positive integer')
    width, height = size
    if width < 1 or height < 1 or fps <= 0:
        raise ValueError('Invalid chunk video profile')
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return False
        if (round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) != width or
                round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) != height or
                abs(cap.get(cv2.CAP_PROP_FPS) - fps) > .01 or
                round(cap.get(cv2.CAP_PROP_FRAME_COUNT)) != expected_frames):
            return False
        for _ in range(expected_frames):
            ok, frame = cap.read()
            if not ok or frame is None or frame.shape[:2] != (height, width):
                return False
        # Some containers report the expected frame count despite extra data.
        ok, _ = cap.read()
        return not ok
    except (cv2.error, OSError):
        return False
    finally:
        cap.release()
