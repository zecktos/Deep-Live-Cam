import platform
import time
from typing import Optional, Tuple

import numpy as np


def is_ndi_available() -> bool:
    """
    Returns True if cyndilib can be imported on this platform.
    """
    if platform.system() not in ("Windows", "Darwin"):
        return False
    try:
        import cyndilib  # noqa: F401  # type: ignore

        return True
    except Exception:
        return False


class NdiVideoCapturer:
    """
    NDI video input capturer.

    Mirrors the minimal interface used by `modules.video_capture.VideoCapturer`:
      - start(width, height, fps) -> bool
      - read() -> (ret, frame_bgr)
      - release() -> None

    Uses the same approach as the working `test.py` example (Finder + Receiver +
    VideoFrameSync + RGBX/RGBA buffer -> numpy).
    """

    def __init__(self, source_name: Optional[str] = None):
        self._source_name = source_name
        self._finder = None
        self._receiver = None
        self._video_frame = None
        self._running = False

    def start(self, width: int = 960, height: int = 540, fps: int = 60) -> bool:
        if not is_ndi_available():
            return False

        try:
            from cyndilib.finder import Finder  # type: ignore
            from cyndilib.receiver import Receiver  # type: ignore
            from cyndilib.video_frame import VideoFrameSync  # type: ignore
            from cyndilib.wrapper.ndi_recv import (  # type: ignore
                RecvColorFormat,
                RecvBandwidth,
            )
        except Exception:
            return False

        try:
            finder = Finder()
            finder.open()

            # Wait up to ~5 seconds for sources to appear.
            finder.wait_for_sources(5000)
            names = finder.get_source_names() or []
            if not names:
                finder.close()
                return False

            selected_name = None
            if self._source_name:
                # Allow matching by full name or stream_name fragment.
                for n in names:
                    if n == self._source_name:
                        selected_name = n
                        break
                if selected_name is None:
                    # Try finding by Source.stream_name
                    for n in names:
                        try:
                            src = finder.get_source(n)
                            if getattr(src, "stream_name", None) == self._source_name:
                                selected_name = n
                                break
                        except Exception:
                            continue
            if selected_name is None:
                selected_name = names[0]

            source = finder.get_source(selected_name)

            receiver = Receiver(
                color_format=RecvColorFormat.RGBX_RGBA,
                bandwidth=RecvBandwidth.highest,
            )
            video_frame = VideoFrameSync()
            receiver.frame_sync.set_video_frame(video_frame)
            receiver.set_source(source)

            # Keep the finder open (matches cyndilib examples and avoids some
            # environments dropping discovery state too early).
            self._finder = finder
            self._receiver = receiver
            self._video_frame = video_frame
            self._running = True

            # Wait a short moment for the first real frame to populate.
            deadline = time.time() + 2.0
            while time.time() < deadline:
                receiver.frame_sync.capture_video()
                if min(video_frame.xres, video_frame.yres) > 0:
                    break
                time.sleep(0.01)

            return True
        except Exception:
            self.release()
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._running or self._receiver is None or self._video_frame is None:
            return False, None

        try:
            self._receiver.frame_sync.capture_video()

            if min(self._video_frame.xres, self._video_frame.yres) == 0:
                return False, None

            frame = np.frombuffer(self._video_frame, dtype=np.uint8).reshape(
                (self._video_frame.yres, self._video_frame.xres, 4)
            )

            # RGBX -> RGB
            rgb = frame[:, :, :3]
            # Convert to BGR for OpenCV pipeline
            bgr = rgb[:, :, ::-1].copy()
            return True, bgr
        except Exception:
            return False, None

    def release(self) -> None:
        self._running = False

        if self._receiver is not None:
            try:
                self._receiver.disconnect()
            except Exception:
                pass
        self._receiver = None
        self._video_frame = None

        if self._finder is not None:
            try:
                self._finder.close()
            except Exception:
                pass
        self._finder = None

