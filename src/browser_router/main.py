import os
from argparse import ArgumentParser
from http.server import HTTPServer

from browser_router.config import get_config
from browser_router.handler import Handler
from browser_router.intlogging import get_logger


def parse_args():
    parser = ArgumentParser(description="Browser router server")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser.parse_args()


def main():
    # Binding to 127.0.0.1 is enough for Docker Desktop (macOS/Windows)
    server = None
    args = parse_args()
    if args.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"

    logger = get_logger(__name__)
    config = get_config()

    logger.debug(f"Config: {config}")
    logger.debug(f"Rulesets: {config.rulesets}")
    logger.debug(f"Chrome profiles: {config.chrome_profiles}")
    logger.debug(f"Default profile: {config.default_profile}")
    logger.debug(f"Domains: {config.domains}")
    
    try:
        logger.info(f"Browser router server started on port {args.port}")
        server = HTTPServer(("127.0.0.1", args.port), Handler)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down browser router server due to KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Error running browser router server: {e}")
        raise
    finally:
        if server is not None:
            server.server_close()


if __name__ == "__main__":
    main()
