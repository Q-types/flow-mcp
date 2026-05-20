"""Entry point for Mind MCP v2 server."""

import asyncio
import sys


def main():
    """Run the Mind MCP server."""
    from .server import run_server

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nMind MCP server stopped.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
