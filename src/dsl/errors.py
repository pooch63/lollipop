"""Errors shared by the linter, the cost counter, and the sandbox."""


class ProgramError(Exception):
    """A candidate is rejected. Callers score it 0."""


class LintError(ProgramError):
    pass


class KillCapExceeded(ProgramError):
    pass


class SandboxError(ProgramError):
    pass
