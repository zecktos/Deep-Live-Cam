import tkinter as tk
import numpy as np
from PIL import Image, ImageTk

from cyndilib.finder import Finder
from cyndilib.receiver import Receiver
from cyndilib.video_frame import VideoFrameSync
from cyndilib.wrapper.ndi_recv import RecvColorFormat, RecvBandwidth


# ---- Discover sources ----
finder = Finder()
finder.open()
finder.wait_for_sources(5000)

names = finder.get_source_names()

if not names:
    print("No NDI sources found")
    exit()

print("Sources:")
for i, n in enumerate(names):
    print(i, n)

source = finder.get_source(names[0])


# ---- Receiver ----
receiver = Receiver(
    color_format=RecvColorFormat.RGBX_RGBA,
    bandwidth=RecvBandwidth.highest,
)

video_frame = VideoFrameSync()
receiver.frame_sync.set_video_frame(video_frame)

receiver.set_source(source)


# ---- Tkinter UI ----
root = tk.Tk()
root.title("NDI Viewer")

label = tk.Label(root)
label.pack()


def update_frame():

    receiver.frame_sync.capture_video()

    if min(video_frame.xres, video_frame.yres) == 0:
        root.after(10, update_frame)
        return

    frame = np.frombuffer(
        video_frame, dtype=np.uint8
    ).reshape((video_frame.yres, video_frame.xres, 4))

    frame = frame[:, :, :3]   # RGBX → RGB

    img = Image.fromarray(frame)
    tkimg = ImageTk.PhotoImage(img)

    label.imgtk = tkimg
    label.configure(image=tkimg)

    root.after(10, update_frame)


update_frame()
root.mainloop()

finder.close()