import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure root logger. Safe to call multiple times."""
    root = logging.getLogger()
    if root.handlers:
        return  # already configured
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "google"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
