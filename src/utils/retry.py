import asyncio
import time
import random
from functools import wraps
from typing import Callable, List, Any, Optional, Type, Union
import logging
from requests import Response
import requests


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 backoff_factor: float = 2.0,
                 retry_on_status: List[int] = None,
                 retry_on_exceptions: List[Type[Exception]] = None,
                 max_backoff: float = 60.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_status = retry_on_status or [429, 500, 502, 503, 504]
        self.retry_on_exceptions = retry_on_exceptions or [
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException
        ]
        self.max_backoff = max_backoff
        self.jitter = jitter


def retry_on_failure(config: RetryConfig = None):
    """Decorator to retry function calls on failure"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Check if result is a Response object with error status
                    if isinstance(result, Response) and result.status_code in config.retry_on_status:
                        if attempt < config.max_retries:
                            backoff_time = calculate_backoff(attempt, config)
                            logger.warning(
                                f"HTTP {result.status_code} error in {func.__name__}, "
                                f"retrying in {backoff_time:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                            )
                            time.sleep(backoff_time)
                            continue
                        else:
                            logger.error(f"Max retries exceeded for {func.__name__}")
                            return result
                    
                    # Success case
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should trigger a retry
                    should_retry = any(isinstance(e, exc_type) for exc_type in config.retry_on_exceptions)
                    
                    if should_retry and attempt < config.max_retries:
                        backoff_time = calculate_backoff(attempt, config)
                        logger.warning(
                            f"Exception {type(e).__name__} in {func.__name__}: {e}, "
                            f"retrying in {backoff_time:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                        )
                        time.sleep(backoff_time)
                        continue
                    else:
                        logger.error(f"Exception in {func.__name__}: {e}")
                        raise
            
            # If we get here, we've exhausted all retries
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def async_retry_on_failure(config: RetryConfig = None):
    """Async decorator to retry function calls on failure"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Check if result is a Response object with error status
                    if isinstance(result, Response) and result.status_code in config.retry_on_status:
                        if attempt < config.max_retries:
                            backoff_time = calculate_backoff(attempt, config)
                            logger.warning(
                                f"HTTP {result.status_code} error in {func.__name__}, "
                                f"retrying in {backoff_time:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                            )
                            await asyncio.sleep(backoff_time)
                            continue
                        else:
                            logger.error(f"Max retries exceeded for {func.__name__}")
                            return result
                    
                    # Success case
                    if attempt > 0:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should trigger a retry
                    should_retry = any(isinstance(e, exc_type) for exc_type in config.retry_on_exceptions)
                    
                    if should_retry and attempt < config.max_retries:
                        backoff_time = calculate_backoff(attempt, config)
                        logger.warning(
                            f"Exception {type(e).__name__} in {func.__name__}: {e}, "
                            f"retrying in {backoff_time:.2f}s (attempt {attempt + 1}/{config.max_retries + 1})"
                        )
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        logger.error(f"Exception in {func.__name__}: {e}")
                        raise
            
            # If we get here, we've exhausted all retries
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def calculate_backoff(attempt: int, config: RetryConfig) -> float:
    """Calculate backoff time for retry attempt"""
    backoff = config.backoff_factor ** attempt
    
    # Cap at max_backoff
    backoff = min(backoff, config.max_backoff)
    
    # Add jitter if enabled
    if config.jitter:
        jitter_range = backoff * 0.1  # 10% jitter
        backoff += random.uniform(-jitter_range, jitter_range)
    
    return max(0, backoff)


class CircuitBreaker:
    """Circuit breaker pattern for handling repeated failures"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                    self.logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful function call"""
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.failure_count = 0
            self.logger.info("Circuit breaker reset to CLOSED state")
    
    def _on_failure(self):
        """Handle failed function call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


def with_timeout(timeout_seconds: float):
    """Decorator to add timeout to function calls"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
            
            # Set up the timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout_seconds))
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Clean up
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        return wrapper
    return decorator


def async_with_timeout(timeout_seconds: float):
    """Async decorator to add timeout to async function calls"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                return result
            except asyncio.TimeoutError:
                raise TimeoutError(f"Async function {func.__name__} timed out after {timeout_seconds} seconds")
        
        return wrapper
    return decorator