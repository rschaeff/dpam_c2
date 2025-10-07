"""
Logging configuration for DPAM pipeline.

Provides structured JSON logging for easy aggregation of SLURM job outputs.
"""

import logging
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, 'prefix'):
            log_data['prefix'] = record.prefix
        if hasattr(record, 'step'):
            log_data['step'] = record.step
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class PlainFormatter(logging.Formatter):
    """Format log records as plain text for console output"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(
    log_file: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    json_format: bool = False
) -> logging.Logger:
    """
    Setup logging configuration for DPAM.
    
    Args:
        log_file: Path to log file (optional)
        console_level: Logging level for console
        file_level: Logging level for file
        json_format: Use JSON format for file logging
    
    Returns:
        Configured root logger
    """
    logger = logging.getLogger('dpam')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler (plain text)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(PlainFormatter())
    logger.addHandler(console_handler)
    
    # File handler (JSON or plain)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(PlainFormatter())
        
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(f'dpam.{name}')


class LogContext:
    """Context manager for adding context to log records"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def log_step_start(logger: logging.Logger, step: str, prefix: str) -> None:
    """Log the start of a pipeline step"""
    logger.info(f"Starting {step} for {prefix}", extra={'step': step, 'prefix': prefix})


def log_step_complete(
    logger: logging.Logger,
    step: str,
    prefix: str,
    duration: float
) -> None:
    """Log the completion of a pipeline step"""
    logger.info(
        f"Completed {step} for {prefix} in {duration:.2f}s",
        extra={'step': step, 'prefix': prefix, 'duration': duration}
    )


def log_step_failed(
    logger: logging.Logger,
    step: str,
    prefix: str,
    error: str
) -> None:
    """Log a failed pipeline step"""
    logger.error(
        f"Failed {step} for {prefix}: {error}",
        extra={'step': step, 'prefix': prefix}
    )
