"""
Agent OS Kernel CLI Entry Point

Usage:
    python -m agent_os_kernel
    python -m agent_os_kernel --help
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Agent OS Kernel - Operating System for AI Agents"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="1.0.0"
    )
    parser.add_argument(
        "--demo",
        choices=["basic", "messaging", "workflow"],
        default="basic",
        help="Run demo"
    )
    
    args = parser.parse_args()
    
    if args.demo == "basic":
        from examples.basic_usage import main as demo_main
    elif args.demo == "messaging":
        from examples.multi_agent_demo import main as demo_main
    elif args.demo == "workflow":
        from examples.complete_workflow import main as demo_main
    
    try:
        import asyncio
        asyncio.run(demo_main())
    except ImportError:
        print("Demo module not found")
        print("Available demos: basic, messaging, workflow")
        sys.exit(1)


if __name__ == "__main__":
    main()
