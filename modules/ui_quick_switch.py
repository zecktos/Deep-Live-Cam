import os
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image, ImageOps

import modules.globals
from modules.utilities import is_image


QUICK_FACE_WINDOW: Optional[ctk.CTkToplevel] = None
QUICK_FACE_SLOT_THUMBS: dict[int, ctk.CTkImage] = {}
QUICK_FACE_SLOT_PICKERS: dict[int, ctk.CTkLabel] = {}


def open_quick_faces_window(
    *,
    root: ctk.CTk,
    img_filetype,
    get_recent_directory_source: Callable[[], Optional[str]],
    set_recent_directory_source: Callable[[Optional[str]], None],
    save_switch_states: Callable[[], None],
    update_status: Callable[[str], None],
    set_source_preview_image: Callable[[str], None],
    invalidate_live_source_face: Callable[[], None],
) -> None:
    """Open or focus a small window with 10 quick face slots."""
    global QUICK_FACE_WINDOW, QUICK_FACE_SLOT_THUMBS, QUICK_FACE_SLOT_PICKERS

    if QUICK_FACE_WINDOW and QUICK_FACE_WINDOW.winfo_exists():
        QUICK_FACE_WINDOW.focus()
        return

    QUICK_FACE_WINDOW = ctk.CTkToplevel(root)
    QUICK_FACE_WINDOW.title("Quick Faces")
    QUICK_FACE_WINDOW.geometry("450x800")
    QUICK_FACE_WINDOW.focus()

    QUICK_FACE_SLOT_THUMBS = {}
    QUICK_FACE_SLOT_PICKERS = {}

    def make_set_command(idx: int):
        return lambda: configure_quick_face_slot(
            idx,
            img_filetype=img_filetype,
            get_recent_directory_source=get_recent_directory_source,
            set_recent_directory_source=set_recent_directory_source,
            save_switch_states=save_switch_states,
        )

    def make_use_command(idx: int):
        return lambda: activate_quick_face_slot(
            idx,
            save_switch_states=save_switch_states,
            update_status=update_status,
            set_source_preview_image=set_source_preview_image,
            invalidate_live_source_face=invalidate_live_source_face,
        )

    for i in range(10):
        slot_label = ctk.CTkLabel(
            QUICK_FACE_WINDOW,
            text=f"Slot {i + 1}",
            width=80,
            anchor="w",
        )
        slot_label.grid(row=i, column=0, padx=(12, 8), pady=6, sticky="w")

        picker_frame = ctk.CTkFrame(
            QUICK_FACE_WINDOW,
            width=58,
            height=58,
            fg_color=("gray90", "gray18"),
            border_width=1,
            border_color=("gray75", "gray28"),
            corner_radius=6,
        )
        picker_frame.grid(row=i, column=1, padx=8, pady=6)
        picker_frame.grid_propagate(False)

        picker_label = ctk.CTkLabel(picker_frame, text="")
        picker_label.place(relx=0.5, rely=0.5, anchor="center")
        QUICK_FACE_SLOT_PICKERS[i] = picker_label

        set_cmd = make_set_command(i)
        picker_frame.bind("<Button-1>", lambda _e, cmd=set_cmd: cmd())
        picker_label.bind("<Button-1>", lambda _e, cmd=set_cmd: cmd())

        use_button = ctk.CTkButton(
            QUICK_FACE_WINDOW,
            text="Use",
            width=80,
            command=make_use_command(i),
        )
        use_button.grid(row=i, column=2, padx=(8, 12), pady=6)

    refresh_quick_faces_thumbnails()


def refresh_quick_faces_thumbnails() -> None:
    """Refresh thumbnails in the Quick Faces window (if open)."""
    global QUICK_FACE_WINDOW, QUICK_FACE_SLOT_THUMBS, QUICK_FACE_SLOT_PICKERS

    if not (QUICK_FACE_WINDOW and QUICK_FACE_WINDOW.winfo_exists()):
        return

    for i in range(10):
        lbl = QUICK_FACE_SLOT_PICKERS.get(i)
        if lbl is None:
            continue

        path = None
        try:
            path = modules.globals.source_slots[i]
        except Exception:
            path = None

        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                img = ImageOps.fit(img, (54, 54), Image.LANCZOS)
                tk_img = ctk.CTkImage(img, size=img.size)
                QUICK_FACE_SLOT_THUMBS[i] = tk_img  # keep reference alive
                lbl.configure(image=tk_img)
            except Exception:
                QUICK_FACE_SLOT_THUMBS.pop(i, None)
                lbl.configure(image=None)
        else:
            QUICK_FACE_SLOT_THUMBS.pop(i, None)
            lbl.configure(image=None)


def configure_quick_face_slot(
    slot_index: int,
    *,
    img_filetype,
    get_recent_directory_source: Callable[[], Optional[str]],
    set_recent_directory_source: Callable[[Optional[str]], None],
    save_switch_states: Callable[[], None],
) -> None:
    """Assign an image path to the given quick face slot."""
    source_path = ctk.filedialog.askopenfilename(
        title="select an source image",
        initialdir=get_recent_directory_source(),
        filetypes=[img_filetype],
    )
    if not is_image(source_path):
        return

    set_recent_directory_source(os.path.dirname(source_path))
    modules.globals.source_slots[slot_index] = source_path
    save_switch_states()
    refresh_quick_faces_thumbnails()


def activate_quick_face_slot(
    slot_index: int,
    *,
    save_switch_states: Callable[[], None],
    update_status: Callable[[str], None],
    set_source_preview_image: Callable[[str], None],
    invalidate_live_source_face: Callable[[], None],
) -> None:
    """Activate a quick face slot for live mode and update source preview."""
    if slot_index < 0 or slot_index >= len(modules.globals.source_slots):
        return

    path = modules.globals.source_slots[slot_index]
    if not path or not is_image(path):
        update_status(f"Slot {slot_index + 1} has no valid image configured.")
        return

    modules.globals.source_path = path
    modules.globals.active_source_slot = slot_index
    save_switch_states()

    invalidate_live_source_face()

    try:
        set_source_preview_image(path)
    except Exception:
        pass

