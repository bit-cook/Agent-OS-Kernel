# API Module

try:
    from .server import AgentOSKernelAPI, run_server
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    AgentOSKernelAPI = None
    run_server = None

__all__ = [
    'AgentOSKernelAPI',
    'run_server',
    '_HAS_FASTAPI',
]

PROVIDER_AVAILABILITY = {
    'fastapi': _HAS_FASTAPI,
}
