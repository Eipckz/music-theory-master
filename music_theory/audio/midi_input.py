"""Live MIDI keyboard input via pygame.midi.

Polled from a Qt timer (no extra threads, no python-rtmidi build needed - works
on Python 3.14). Emits noteOn/noteOff so piano exercises can grade real
keyboard playing. Degrades silently if no MIDI hardware/library is present."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class MidiInput(QObject):
    noteOn = pyqtSignal(int, int)   # midi, velocity
    noteOff = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._midi = None
        self._input = None
        self._timer = QTimer(self)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._poll)
        self.device_name = ""
        self.available = False

    def list_devices(self) -> list[str]:
        try:
            import pygame.midi as pm
            if not pm.get_init():
                pm.init()
            names = []
            for i in range(pm.get_count()):
                info = pm.get_device_info(i)
                is_input = info[2]
                if is_input:
                    names.append(info[1].decode(errors="ignore"))
            return names
        except Exception:  # noqa: BLE001
            return []

    def start(self, name_substr: str = "") -> bool:
        self.stop()
        try:
            import pygame.midi as pm
            if not pm.get_init():
                pm.init()
            self._midi = pm
            dev_id = self._find_input(pm, name_substr)
            if dev_id is None:
                return False
            self._input = pm.Input(dev_id)
            self.device_name = pm.get_device_info(dev_id)[1].decode(errors="ignore")
            self.available = True
            self._timer.start()
            return True
        except Exception:  # noqa: BLE001 - missing hardware/driver is fine
            self.available = False
            return False

    def _find_input(self, pm, name_substr: str) -> Optional[int]:
        default = pm.get_default_input_id()
        match = None
        for i in range(pm.get_count()):
            info = pm.get_device_info(i)
            if info[2]:  # is input
                nm = info[1].decode(errors="ignore")
                if name_substr and name_substr.lower() in nm.lower():
                    return i
                if match is None:
                    match = i
        if name_substr:
            return None
        return default if default != -1 else match

    def _poll(self) -> None:
        if self._input is None:
            return
        try:
            if not self._input.poll():
                return
            for event in self._input.read(64):
                data, _ts = event
                status, d1, d2 = data[0], data[1], data[2]
                msg = status & 0xF0
                if msg == 0x90 and d2 > 0:
                    self.noteOn.emit(d1, d2)
                elif msg == 0x80 or (msg == 0x90 and d2 == 0):
                    self.noteOff.emit(d1)
        except Exception:  # noqa: BLE001
            self.stop()

    def stop(self) -> None:
        self._timer.stop()
        try:
            if self._input is not None:
                self._input.close()
        except Exception:  # noqa: BLE001
            pass
        self._input = None
        self.available = False
