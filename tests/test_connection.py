from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from jupyhop.connection import ConnectionPool
from jupyhop.ssh import SSHTransport


def test_closing_pool_attempts_every_owned_connection_even_if_one_cleanup_fails():
    pool = ConnectionPool(batch=True)
    first, failed, last = Mock(), Mock(side_effect=RuntimeError("fixture cleanup error")), Mock()
    pool.connections = {
        SSHTransport("first"): SimpleNamespace(close=first),
        SSHTransport("failed"): SimpleNamespace(close=failed),
        SSHTransport("last"): SimpleNamespace(close=last),
    }
    with pytest.raises(RuntimeError, match="fixture cleanup"):
        pool.close()
    for close in (first, failed, last):
        close.assert_called_once_with()
    assert not pool.connections


def test_explicit_tunnel_cancellation_discards_only_its_owned_route():
    pool = ConnectionPool(batch=True)
    first, other = Mock(), Mock()
    pool.connections = {SSHTransport("first"): first, SSHTransport("other"): other}
    pool.discard(SSHTransport("first", connections=pool))
    pool.discard(SSHTransport("first", connections=pool))
    first.close.assert_called_once_with()
    other.close.assert_not_called()
    assert list(pool.connections) == [SSHTransport("other")]
