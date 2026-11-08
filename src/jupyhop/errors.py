"""Public failures contain curated text, never raw SSH or remote output."""


class JupyHopError(Exception):
    exit_code = 3


class SSHError(JupyHopError):
    pass


class PrerequisiteError(JupyHopError):
    exit_code = 4


class ProtocolError(JupyHopError):
    exit_code = 5


class DiscoveryError(JupyHopError):
    exit_code = 6


class SelectionError(JupyHopError):
    exit_code = 7


class TunnelError(JupyHopError):
    exit_code = 8


class OwnershipError(JupyHopError):
    exit_code = 11
