"""Public failures contain curated text, never raw SSH or remote output."""


class JupyHopError(Exception):
    exit_code = 3


class SSHError(JupyHopError):
    pass


class PrerequisiteError(JupyHopError):
    exit_code = 4


class ProtocolError(JupyHopError):
    exit_code = 5
