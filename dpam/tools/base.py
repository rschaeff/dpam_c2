"""
Base class for external tool wrappers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess
import shutil

from dpam.utils.logging_config import get_logger

logger = get_logger('tools')


class ExternalTool(ABC):
    """
    Abstract base class for external tool wrappers.
    
    Provides common functionality for checking tool availability,
    executing commands, and handling errors.
    """
    
    def __init__(
        self,
        executable: str,
        check_available: bool = True,
        required: bool = True
    ):
        """
        Initialize tool wrapper.
        
        Args:
            executable: Name or path of executable
            check_available: Check if tool is in PATH
            required: Raise error if tool not found
        """
        self.executable = executable
        self.available = False
        
        if check_available:
            self.available = self._check_availability()
            
            if not self.available and required:
                raise RuntimeError(
                    f"{executable} not found in PATH. "
                    f"Please install {executable} and ensure it's in your PATH."
                )
    
    def _check_availability(self) -> bool:
        """Check if tool is available in PATH"""
        result = shutil.which(self.executable)
        
        if result:
            logger.debug(f"Found {self.executable} at {result}")
            return True
        else:
            logger.warning(f"{self.executable} not found in PATH")
            return False
    
    def _execute(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        log_file: Optional[Path] = None,
        capture_output: bool = False,
        check: bool = True,
        env: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """
        Execute command with logging.

        Args:
            cmd: Command and arguments
            cwd: Working directory
            log_file: Optional log file for stdout/stderr
            capture_output: Capture stdout/stderr
            check: Raise exception on non-zero exit code
            env: Optional environment variables dict

        Returns:
            CompletedProcess result
        """
        logger.debug(f"Executing: {' '.join(str(c) for c in cmd)}")

        kwargs = {
            'cwd': cwd,
            'text': True,
        }

        # Always preserve environment (especially conda env) unless explicitly overridden
        if env is not None:
            kwargs['env'] = env
        else:
            import os
            kwargs['env'] = os.environ.copy()
        
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    **kwargs
                )
        elif capture_output:
            result = subprocess.run(
                cmd,
                capture_output=True,
                **kwargs
            )
        else:
            result = subprocess.run(cmd, **kwargs)
        
        if check and result.returncode != 0:
            error_msg = f"{self.executable} failed with return code {result.returncode}"
            if capture_output and result.stderr:
                error_msg += f"\nStderr: {result.stderr}"
            logger.error(error_msg)
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                result.stdout,
                result.stderr
            )
        
        return result
    
    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Run the tool with specified parameters"""
        pass
    
    def is_available(self) -> bool:
        """Check if tool is available"""
        return self.available
