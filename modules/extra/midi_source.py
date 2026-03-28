from __future__ import annotations

import threading
from typing import Optional

try:
    import mido
except Exception:  # pragma: no cover - optional dependency
    mido = None  # type: ignore

import modules.globals
from modules.extra.triggers import TriggerSource, TriggerType, TriggerEvent, handle_trigger


class MidiTriggerSource(TriggerSource):
    """
    Optional MIDI backend that emits TriggerEvent(NOTE, note_number, velocity)
    into the generic trigger manager.
    """

    def __init__(self) -> None:
        self._input: Optional["mido.ports.BaseInput"] = None  # type: ignore[name-defined]
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if mido is None:
            return

        if self._thread and self._thread.is_alive():
            return

        try:
            port_name = modules.globals.quick_face_midi_port

            # If the user selected a specific port and it's available, open it.
            if port_name and port_name in mido.get_input_names():
                self._input = mido.open_input(port_name)  # type: ignore[assignment]
            else:
                # No specific port selected: try to create a named virtual port
                # so other software can send to "Deep-Live-Cam" directly.
                try:
                    self._input = mido.open_input("Deep-Live-Cam", virtual=True)  # type: ignore[assignment]
                except Exception:
                    # Fallback: open the default input port.
                    self._input = mido.open_input()  # type: ignore[assignment]
        except Exception:
            self._input = None
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="MidiTriggerSource", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None

        if self._input is not None:
            try:
                self._input.close()
            except Exception:
                pass
            self._input = None

    def _loop(self) -> None:
        if self._input is None:
            return

        while not self._stop.is_set():
            try:
                msg = self._input.poll()
            except Exception:
                break

            if msg is None:
                self._stop.wait(0.01)
                continue

            # We only care about note_on with velocity > 0 for now.
            if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
                note = int(getattr(msg, "note", 0))
                vel = float(getattr(msg, "velocity", 0))
                event = TriggerEvent(type=TriggerType.NOTE, code=note, value=vel)
                handle_trigger(event)

