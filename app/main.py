"""Entry point: `python -m app.main` starts the MCP server over stdio."""

import logging
import sys

from dotenv import load_dotenv

from app.tools.mcp_server import build_server


def main() -> None:
    load_dotenv()
    # stdout carries the MCP protocol, so logs must go to stderr.
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    build_server().run()


if __name__ == "__main__":
    main()
