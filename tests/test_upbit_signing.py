from autotrade.exchanges.upbit import UpbitClient, UpbitCreds


def test_upbit_signing_smoke():
    c = UpbitClient(creds=UpbitCreds(access_key="A", secret_key="S"))
    # private 헤더 생성이 예외 없이 되는지만 본다
    h = c._jwt_headers(
        {"market": "KRW-BTC", "side": "bid", "ord_type": "price", "price": "10000"}
    )
    assert "Authorization" in h
