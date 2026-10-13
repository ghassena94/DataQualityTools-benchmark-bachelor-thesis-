####################################################
# Helpers for measuring how much memory a detector needs.
#
# The peak has to be a peak of the window, not of the process. ru_maxrss is no
# good for that: it never decreases, so it still carries whatever peaked before
# the detector ran. Loading adult leaves about 15 MB of that behind, which is
# more than the detector goes on to need, so the delta comes out 0.
#
# ru_maxrss is still recorded, as a cross check.
####################################################

import ctypes
import gc
import resource
import sys
import threading
import time
import tracemalloc

import numpy as np
import psutil

_process = psutil.Process()


def current_rss():
    """Memory this process is using right now, in bytes."""
    return _process.memory_info().rss


def rss_unit():
    """getrusage reports ru_maxrss in bytes on macOS and in kibibytes on Linux."""
    return "bytes" if sys.platform == "darwin" else "kibibytes"


def max_rss():
    """Highest RSS this process has reached since it started, in bytes.

    Recorded for comparison only. It cannot be reset, so it carries the peak of
    everything that ran before the window as well.
    """
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss_unit() == "bytes":
        return value
    return value * 1024


def trim_allocator():
    """Hands the pages the allocator is sitting on back to the OS.

    Without this the detector allocates into memory that is already resident and
    the RSS delta lands several MB under what tracemalloc counted: 1.6 MB against
    6.7 MB on har. After trimming the two agree. glibc only, so it does nothing
    on macOS and the record says whether it ran.
    """
    gc.collect()

    if not sys.platform.startswith("linux"):
        return False
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        return False
    return True


def _read_status(field):
    """Reads one bytes-valued field out of /proc/self/status. Linux only."""
    try:
        with open("/proc/self/status") as handle:
            for line in handle:
                if line.startswith(field):
                    return int(line.split()[1]) * 1024
    except IOError:
        return None
    return None


class PeakTracker:
    """Tracks the highest RSS reached inside the window.

    On linux the kernel does the work: writing 5 to /proc/self/clear_refs resets
    VmHWM to the current RSS, so VmHWM afterwards is the peak of the window and
    nothing else. It is exact and it cannot miss a spike.

    Anywhere else there is no way to reset a peak counter, so it falls back to
    watching current RSS on a thread, which can miss a spike shorter than the
    interval. Which one was used is recorded with the measurement.
    """

    def __init__(self, interval=0.001):
        self.interval = interval
        self.peak = 0
        self.method = None
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        self.peak = current_rss()

        if self._reset_peak():
            self.method = "clear_refs"
        else:
            self.method = "sampler"
            self._thread = threading.Thread(target=self._run)
            self._thread.daemon = True
            self._thread.start()
        return self

    def _reset_peak(self):
        if not sys.platform.startswith("linux"):
            return False
        if _read_status("VmHWM:") is None:
            return False
        try:
            with open("/proc/self/clear_refs", "w") as handle:
                handle.write("5")
        except IOError:
            return False
        return True

    def _run(self):
        while not self._stop.is_set():
            value = current_rss()
            if value > self.peak:
                self.peak = value
            time.sleep(self.interval)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.method == "clear_refs":
            self.peak = _read_status("VmHWM:")
            return False

        self._stop.set()
        self._thread.join()

        # one last look, in case the window ended between two samples
        value = current_rss()
        if value > self.peak:
            self.peak = value
        return False


def tracemalloc_coverage(size=8 * 1024 * 1024):
    """Allocates an array of a known size and reports the fraction tracemalloc saw.

    This is here so the coverage caveat can be quoted from a measurement instead
    of assumed. numpy registers itself with tracemalloc, so on this setup it
    comes out at 1.0 and the caveat is about the tools that allocate outside
    python altogether, not about numpy.

    Call it after the measurement window, never before: it pushes up the process
    high water mark and ru_maxrss does not come back down.
    """
    tracemalloc.start()
    array = np.ones(size // 8, dtype=np.float64)
    observed = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    del array

    return {
        "probe_allocated_bytes": size,
        "probe_observed_bytes": observed,
        "probe_coverage": observed / size,
    }
