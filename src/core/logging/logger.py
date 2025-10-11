"""Structured logging setup with dual output"""

import structlog
import logging
import sys
from pathlib import Path

def setup_logging(
    mode: str = "production",
    terminal_level: str = "ERROR",  # ZMĚNA: Jen ERROR v production
    file_level: str = "DEBUG",
    log_file: str = "logs/voice_assistant.log"
):
    """
    Setup dual logging:
    - Terminal: minimal output (ERROR+ in production, INFO+ in dev)
    - File: complete logs (DEBUG+)
    """
    # Vytvoř logs složku
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Určí terminal level podle módu
    if mode == "development":
        terminal_level = "DEBUG"
        use_colors = True
    else:
        terminal_level = "ERROR"  # PRODUCTION: Jen errory
        use_colors = False

    terminal_log_level = getattr(logging, terminal_level.upper(), logging.ERROR)
    file_log_level = getattr(logging, file_level.upper(), logging.DEBUG)

    # ===== FILE HANDLER =====
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(file_log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # ===== CONSOLE HANDLER =====
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(terminal_log_level)

    if mode == "development":
        console_formatter = logging.Formatter('%(message)s')
    else:
        console_formatter = logging.Formatter('❌ %(message)s')  # Jen errors

    console_handler.setFormatter(console_formatter)

    # ===== ROOT LOGGER =====
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # ===== STRUCTLOG =====
    if mode == "development":
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(colors=use_colors)
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # PRODUCTION: Jen do souboru, terminál ignoruj
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR),  # ZMĚNA
            cache_logger_on_first_use=True,
        )

    # Suppress všechny third-party loggery
    for logger_name in ["httpx", "httpcore", "openai", "groq", "urllib3", "openwakeword"]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    return root_logger

def setup_production_logging(log_file: str = "logs/voice_assistant.log"):
    """Production mode - čistý terminál, jen errory"""
    return setup_logging(mode="production", log_file=log_file)

def setup_dev_logging(log_file: str = "logs/voice_assistant.log"):
    """Development mode - verbose terminál"""
    return setup_logging(mode="development", log_file=log_file)
