import time
from unittest.mock import patch, MagicMock


def test_backoff_doubles_up_to_max():
    delays = []
    def fake_sleep(t):
        delays.append(t)

    # Simule 6 echecs de connexion
    call_count = [0]
    def fake_connect(*a):
        call_count[0] += 1
        if call_count[0] < 7:
            raise ConnectionRefusedError("refused")

    with patch("time.sleep", fake_sleep), \
         patch("socket.socket") as mock_sock:
        mock_sock.return_value.connect.side_effect = fake_connect
        # importer apres patch pour eviter l'execution au import
        import importlib, client as c
        # on teste la fonction isolee
        result = c._compute_backoff_delays(6)  # fonction helper a creer

    assert result == [1, 2, 4, 8, 16, 32]


def test_backoff_capped_at_60():
    result = __import__("client")._compute_backoff_delays(10)
    assert all(d <= 60 for d in result)
    assert result[-1] == 60
