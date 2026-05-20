def test_backoff_doubles_up_to_max():
    import client as c
    result = c._compute_backoff_delays(6)
    assert result == [1, 2, 4, 8, 16, 32]


def test_backoff_capped_at_60():
    result = __import__("client")._compute_backoff_delays(10)
    assert all(d <= 60 for d in result)
    assert result[-1] == 60
