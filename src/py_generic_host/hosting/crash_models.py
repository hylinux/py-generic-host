from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CrashInfo:
    source: str
    exception: BaseException
