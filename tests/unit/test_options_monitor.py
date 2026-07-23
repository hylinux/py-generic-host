import pytest

from py_generic_host.config.monitor import OptionsMonitor


@pytest.mark.asyncio
async def test_options_monitor_reload_triggers_listener():
    state = {"v": 1}

    monitor = OptionsMonitor(lambda: state["v"])

    received: list[int] = []

    monitor.on_change(lambda v: received.append(v))

    state["v"] = 2

    await monitor.reload()
    assert received == [2]

    assert monitor.current_value == 2


@pytest.mark.asyncio
async def test_options_monitor_no_change_no_notify():

    state = {"v" : "a"}

    monitor = OptionsMonitor(lambda : state["v"])

    called: list = []

    monitor.on_change(lambda v: called.append(v))

    await monitor.reload()
    assert called == []

