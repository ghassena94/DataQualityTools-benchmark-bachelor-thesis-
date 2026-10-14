"""Make os.cpu_count() return REIN_WORKERS (server plan 2026-10-13, P0 step 5, U3).

Python imports this file at startup because docker-compose.server.yml puts
/rein/server_env on PYTHONPATH. Raha starts its strategy workers with
multiprocessing.Pool(), which takes os.cpu_count() workers: 10 on the Mac's
Docker VM, 192 on the server. With REIN_WORKERS=10 the server starts 10 too.

multiprocessing.cpu_count() and Pool() both call os.cpu_count() when they run,
so replacing os.cpu_count is enough and multiprocessing is not imported here.
Nothing else changes. Without REIN_WORKERS (or with it empty) this file does
nothing. A value that is not a positive integer stops Python with a message,
so a typo cannot silently fall back to 192 workers.

This shadows Ubuntu's /usr/lib/python3.8/sitecustomize.py, which only installs
the apport exception hook; apport is not installed in the image, so that file
does nothing there either (checked 14 Oct: "No module named 'apport_python_hook'").
"""
import os

_value = os.environ.get("REIN_WORKERS", "").strip()
if _value:
    if not _value.isdigit() or int(_value) < 1:
        # os.write: unbuffered, so the message survives os._exit (stderr is block-buffered in 3.8)
        os.write(2, ("sitecustomize: REIN_WORKERS must be a positive integer, got %r\n" % _value).encode())
        os._exit(2)
    _workers = int(_value)

    def cpu_count():
        """Return REIN_WORKERS instead of the number of CPUs of the host."""
        return _workers

    os.cpu_count = cpu_count
del _value
