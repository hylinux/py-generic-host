from collections.abc import Callable

from py_generic_host.hosting.crash_models import CrashInfo

CrashHandler = Callable[[CrashInfo], None]
