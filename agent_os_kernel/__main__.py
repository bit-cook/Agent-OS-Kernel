"""
Agent OS Kernel CLI Entry Point

Usage:
    python -m agent_os_kernel --help
    python -m agent_os_kernel doctor
    python -m agent_os_kernel create -n "Researcher" -t "Research AI"
    python -m agent_os_kernel demo --type checkpoint
"""

import sys

from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())
