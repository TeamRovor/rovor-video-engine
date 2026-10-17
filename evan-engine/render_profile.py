"""Development output geometry; animation time is always seconds."""
import math

DEFAULT_FPS = 60
LANDSCAPE = (1920, 1080)
VERTICAL = (1080, 1920)


def frame_count(duration, fps=DEFAULT_FPS):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Duration must be positive and finite")
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        raise ValueError("FPS must be an integer between 1 and 120")
    return math.ceil(duration * fps)


class ScaledDraw:
    """Draw the existing 1280x720 layout directly on the output canvas.

    Text and vector marks are rasterized at output size; character plates are
    independently resampled by the renderer, never a whole-frame upscale.
    """
    def __init__(self, image, scale):
        from PIL import ImageDraw
        self.draw = ImageDraw.Draw(image)
        self.scale = scale

    def __getattr__(self, name):
        method = getattr(self.draw, name)
        def draw(xy, *args, **kwargs):
            xy = tuple(round(v * self.scale) for v in xy)
            for key in ("width", "radius"):
                if key in kwargs:
                    kwargs[key] = max(1, round(kwargs[key] * self.scale))
            if "font" in kwargs:
                f = kwargs["font"]
                kwargs["font"] = f.font_variant(size=round(f.size * self.scale))
            return method(xy, *args, **kwargs)
        return draw
