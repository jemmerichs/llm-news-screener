from pathlib import Path
from loguru import logger
from src.config import LoggingConfig
import os

def setup_logging(config: LoggingConfig) -> None:
    """
    Configure application logging using loguru.
    
    Args:
        config: Logging configuration object
    """
    # Remove default handlers
    logger.remove()
    
    # Console handler
    logger.add(lambda msg: print(msg, end=""), colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # File handler
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    print("Log file path:", os.path.abspath(log_file))
    logger.add(log_file, rotation="10 MB", retention="10 days", encoding="utf-8", enqueue=True, backtrace=True, diagnose=True, level="DEBUG")
    
    # Optionally apply config
    if config:
        # You can add more config-based handlers here if needed
        pass
    
    logger.info("Logging system initialized") 