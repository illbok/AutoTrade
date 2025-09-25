from autotrade.exchanges.upbit import UpbitClient


def test_live_guard_default_dryrun():
    c = UpbitClient(live=False, creds=None)
    assert c.live is False
