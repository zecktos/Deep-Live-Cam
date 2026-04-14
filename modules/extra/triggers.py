from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Optional, Any

import customtkinter as ctk

import modules.globals

from time import sleep
from threading import Thread



class TriggerType(str, Enum):
    NOTE = "note"  # Generic "note" trigger (e.g. MIDI)
    KEY = "key"  # Keyboard key
    OSC = "osc"  # OSC address/value pair


@dataclass
class TriggerEvent:
    type: TriggerType
    code: Any
    value: Optional[float] = None


class TriggerSource(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


_sources: list[TriggerSource] = []
_root: Optional[ctk.CTk] = None


def init_trigger_manager(root: ctk.CTk) -> None:
    """Provide the Tk root so triggers can safely schedule UI work."""
    global _root
    _root = root


def register_source(src: TriggerSource) -> None:
    _sources.append(src)
    try:
        src.start()
    except Exception:
        # Source startup failure should not break the app.
        pass


def shutdown_sources() -> None:
    for src in _sources:
        try:
            src.stop()
        except Exception:
            pass
    _sources.clear()


def _match_event_to_slot(event: TriggerEvent) -> Optional[int]:
    bindings = modules.globals.quick_face_triggers
    for idx, meta in enumerate(bindings):
        if meta is None:
            continue
        if meta.get("type") != event.type.value:
            continue
        if meta.get("code") != event.code:
            continue
        return idx
    return None

def transparency_change(value: float):
        from modules.ui import update_status
        # Convert slider value to float
        val = float(value)
        modules.globals.opacity = val  # Set global opacity
        percentage = int(val * 100)

        if percentage == 0:
            modules.globals.fp_ui["face_enhancer"] = False
            update_status("Transparency set to 0% - Face swapping disabled.")
        elif percentage == 100:
            modules.globals.face_swapper_enabled = True
            update_status("Transparency set to 100%.")
        else:
            modules.globals.face_swapper_enabled = True
            update_status(f"Transparency set to {percentage}%")

def handle_trigger(event: TriggerEvent) -> None:
    """Dispatch an incoming trigger event to the appropriate quick face slot, if any."""
    
    if _root is None:
        return
    
    slot_index = _match_event_to_slot(event)

    if slot_index is None:
        # check for magic values to trigger hacky opacity fade
        if event.code == 126 or event.code == 127 :
            def opacity_fade(sec, startVal) :
                if startVal > 0 :
                    startVal = 1
                    print("fade to 1")
                else :
                    startVal = 0
                    print("fade to 0")
                print("fade time:", sec)
                if sec <= 0 :
                    transparency_change(abs(startVal - 1))
                    return
                if sec > 20 :
                    sec = 20

                s = 0.5/sec
                v = startVal
                transparency_change(v)
                for t in range(0,int(sec*2)) :
                    if startVal == 1 :
                        v = v - s
                    else :
                         v = v + s
                    transparency_change(v)
                    print("value", v)
                    sleep(0.5)
                print("thread exit")

            def _activate() -> None:
                global activeFadeThread
                if event.code == 126 :
                    fade_Thread = Thread(target=opacity_fade, args=(event.value,0,))
                    fade_Thread.start()
                if event.code == 127 :
                    fade_Thread = Thread(target=opacity_fade, args=(event.value,1,))
                    fade_Thread.start()
                    
        else :
            return

    else :
        def _activate() -> None:
            # Use the same helpers as the Quick Faces UI.
            from modules.ui import (  # local import to avoid cycles at module import time
                save_switch_states,
                update_status,
                source_label,
            )

            # Import here to avoid circular imports between ui_quick_switch and this module.
            from modules.ui_quick_switch import activate_quick_face_slot

            def _set_source_preview_image(path: str) -> None:
                # Reuse the same pattern as open_quick_faces_window for preview.
                # update_source_preview in ui.py already handles the actual image, so use that.
                try:
                    from modules.ui import render_image_preview

                    image = render_image_preview(path, (200, 200))
                    source_label.configure(image=image)
                except Exception:
                    pass

            def _invalidate_live_source_face() -> None:
                # Reset the cached live source face so the next live frame
                # recomputes it using the newly selected source_path.
                import modules.ui as ui_mod

                ui_mod.LIVE_SOURCE_FACE = None

            activate_quick_face_slot(
                slot_index,
                save_switch_states=save_switch_states,
                update_status=update_status,
                set_source_preview_image=_set_source_preview_image,
                invalidate_live_source_face=_invalidate_live_source_face,
            )

    # Ensure we run on the Tk mainloop thread.
    try:
        _root.after(0, _activate)
    except Exception:
        _activate()

