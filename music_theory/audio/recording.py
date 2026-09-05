"""Explicit, bounded microphone capture; no device opens until Start is called."""
from __future__ import annotations

import threading
import numpy as np


class MicrophoneRecorder:
    def __init__(self):
        self.stream = None
        self.sample_rate = 16000
        self._chunks = []
        self._count = 0
        self._limit = 0
        self._lock = threading.Lock()
        self.status = ""

    @staticmethod
    def devices():
        import sounddevice as sd
        return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]

    def start(self, device=None, seconds=5):
        import sounddevice as sd
        if self.stream is not None:
            raise ValueError("A recording is already in progress.")
        if not 1 <= seconds <= 30:
            raise ValueError("Record between 1 and 30 seconds.")
        info = sd.query_devices(device, "input")
        self.sample_rate = int(info["default_samplerate"])
        self._limit = self.sample_rate * seconds
        self._chunks = []
        self._count = 0
        self.status = ""
        try:
            self.stream = sd.InputStream(device=device, samplerate=self.sample_rate, channels=1,
                                         dtype="float32", callback=self._callback)
            self.stream.start()
        except Exception:
            self.close()
            raise

    def _callback(self, data, frames, time_info, status):
        with self._lock:
            if status:
                self.status = str(status)
            room = max(0, self._limit - self._count)
            if room:
                chunk = data[:room, 0].copy()
                self._chunks.append(chunk)
                self._count += len(chunk)

    def stop(self):
        self.close()
        with self._lock:
            samples = np.concatenate(self._chunks) if self._chunks else np.array([], dtype=np.float32)
            self._chunks = []
        return samples, self.sample_rate

    def close(self):
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
            except Exception as exc:
                self.status = f"Input stopped with a device error: {exc}"
            finally:
                try:
                    stream.close()
                except Exception as exc:
                    self.status = f"Input close error: {exc}"
