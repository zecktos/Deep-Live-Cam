import platform
from fractions import Fraction
from typing import Optional

import numpy as np
import cv2


def is_ndi_output_available() -> bool:
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


class NdiVideoSender:
    """
    Simple NDI video sender used as an output sink.

    API:
      - start(stream_name: str, width: int, height: int, fps: int) -> bool
      - send_frame(frame_bgr: np.ndarray) -> None
      - close() -> None
    """

    def __init__(self, stream_name: str = "Deep-Live-Cam"):
        self._stream_name = stream_name
        self._sender = None
        self._width: int | None = None
        self._height: int | None = None

    def start(self, width: int, height: int, fps: int = 30) -> bool:
        if not is_ndi_output_available():
            return False

        try:
            from cyndilib.sender import Sender  # type: ignore
            from cyndilib.video_frame import VideoSendFrame  # type: ignore
            from cyndilib.wrapper.ndi_structs import FourCC  # type: ignore
        except Exception:
            return False

        try:
            snd = Sender(self._stream_name)

            # Configure a VideoSendFrame matching our preview size and fps.
            vf = VideoSendFrame()
            vf.set_resolution(width, height)
            vf.set_frame_rate(Fraction(fps))
            # Use a packed RGBA-like format; we'll send BGRA data.
            vf.set_fourcc(FourCC.BGRA)

            snd.set_video_frame(vf)

            # Explicitly open the sender so it starts advertising the NDI source.
            snd.open()
        except Exception:
            return False

        self._sender = snd
        self._width = width
        self._height = height
        return True

    def send_frame(self, frame_bgr: np.ndarray) -> None:
        if self._sender is None:
            return
        if frame_bgr is None:
            return
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            return

        # Ensure the frame matches the resolution configured in VideoSendFrame.
        if self._width is not None and self._height is not None:
            if frame_bgr.shape[1] != self._width or frame_bgr.shape[0] != self._height:
                frame_bgr = cv2.resize(
                    frame_bgr, (self._width, self._height), interpolation=cv2.INTER_LINEAR
                )

        h, w, _ = frame_bgr.shape

        # Convert BGR -> BGRA (alpha=255) as a contiguous 1D buffer.
        bgra = np.concatenate(
            [
                frame_bgr.astype(np.uint8),
                255 * np.ones((h, w, 1), dtype=np.uint8),
            ],
            axis=2,
        )
        data = bgra.ravel()

        try:
            self._sender.write_video(data)
        except Exception as e:
            # Do not let NDI failures break the preview loop, but log for debugging.
            print(f"NDI output send_frame error: {e}")

    def close(self) -> None:
        if self._sender is not None:
            try:
                self._sender.close()
            except Exception:
                pass
        self._sender = None

