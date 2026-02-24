# -*- coding: utf-8 -*-
"""
HTTP Client Module

A robust async HTTP client with connection pooling, retry mechanism,
timeout handling, and circuit breaker integration.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict, List, Union
from functools import wraps
import logging
from urllib.parse import urljoin, urlencode
from aiohttp import ClientSession, ClientTimeout, ClientError, TCPConnector
from aiohttp.client import _RequestContextManager
import json

from .circuit_breaker import CircuitBreaker, CircuitState, CircuitError
from .retry_mechanism import RetryPolicy, RetryableError

logger = logging.getLogger(__name__)


class HttpMethod(Enum):
    """HTTP methods supported by the client."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HttpStatus(Enum):
    """Common HTTP status codes."""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class HttpError(Exception):
    """Exception raised for HTTP errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        request_url: Optional[str] = None,
        request_method: Optional[str] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.request_url = request_url
        self.request_method = request_method


class HttpClientError(HttpError):
    """Exception for client-side errors (4xx)."""
    pass


class HttpServerError(HttpError):
    """Exception for server-side errors (5xx)."""
    pass


@dataclass
class HttpRequest:
    """HTTP request configuration."""
    url: str
    method: HttpMethod = HttpMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Any = None
    json_data: Any = None
    timeout: float = 30.0
    follow_redirects: bool = True
    max_redirects: int = 10
    allow_retries: bool = True
    retry_count: int = 3
    retry_backoff: float = 1.0
    retry_max_backoff: float = 60.0
    use_circuit_breaker: bool = True
    circuit_failure_threshold: int = 5
    circuit_timeout_seconds: float = 30.0
    
    def __post_init__(self):
        """Set default headers."""
        if "Content-Type" not in self.headers and (self.data or self.json_data):
            if self.json_data:
                self.headers["Content-Type"] = "application/json"
            elif isinstance(self.data, str):
                self.headers["Content-Type"] = "text/plain"
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = "OpenClaw-HTTP-Client/1.0"


@dataclass
class HttpResponse:
    """HTTP response wrapper."""
    status_code: int
    headers: Dict[str, str]
    body: Any
    text: str
    json: Any
    url: str
    method: str
    elapsed_time: float
    request: Optional[HttpRequest] = None
    
    @property
    def ok(self) -> bool:
        """Check if response is successful (2xx)."""
        return 200 <= self.status_code < 300
    
    @property
    def is_client_error(self) -> bool:
        """Check if response is a client error (4xx)."""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self) -> bool:
        """Check if response is a server error (5xx)."""
        return 500 <= self.status_code < 600
    
    def raise_for_status(self):
        """Raise exception for error status codes."""
        if self.is_client_error:
            raise HttpClientError(
                f"Client error: {self.status_code}",
                status_code=self.status_code,
                response_body=self.text,
                request_url=self.url,
                request_method=self.method
            )
        elif self.is_server_error:
            raise HttpServerError(
                f"Server error: {self.status_code}",
                status_code=self.status_code,
                response_body=self.text,
                request_url=self.url,
                request_method=self.method
            )


@dataclass
class HttpClientConfig:
    """Configuration for HTTP client."""
    base_url: Optional[str] = None
    default_timeout: float = 30.0
    max_connections: int = 100
    max_connections_per_host: int = 10
    connection_timeout: float = 10.0
    enable_keepalive: bool = True
    keepalive_timeout: int = 30
    max_redirects: int = 10
    default_headers: Dict[str, str] = field(default_factory=dict)
    default_params: Dict[str, Any] = field(default_factory=dict)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_failure_threshold: int = 5
    circuit_timeout_seconds: float = 30.0
    circuit_success_threshold: int = 3
    enableCircuitBreaker: bool = True


class HttpClient:
    """
    Async HTTP client with connection pooling, retry, and circuit breaker.
    
    Example:
        >>> client = HttpClient(base_url="https://api.example.com")
        >>> response = await client.get("/users")
        >>> print(response.json)
    """
    
    _instances: Dict[str, "HttpClient"] = {}
    
    def __init__(self, config: Optional[HttpClientConfig] = None):
        """
        Initialize HTTP client.
        
        Args:
            config: Optional client configuration
        """
        self.config = config or HttpClientConfig()
        self._session: Optional[ClientSession] = None
        self._connector: Optional[TCPConnector] = None
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._closed = False
        self._lock = asyncio.Lock()
        
    @classmethod
    def get_instance(cls, name: str = "default") -> "HttpClient":
        """Get or create a named client instance."""
        if name not in cls._instances:
            cls._instances[name] = cls()
        return cls._instances[name]
    
    @classmethod
    def reset_instance(cls, name: str = "default"):
        """Reset a named client instance."""
        if name in cls._instances:
            instance = cls._instances[name]
            asyncio.create_task(instance.close())
            del cls._instances[name]
    
    async def _get_circuit_breaker(self, host: str) -> CircuitBreaker:
        """Get or create circuit breaker for a host."""
        if host not in self._circuit_breakers:
            self._circuit_breakers[host] = CircuitBreaker(
                name=f"http_{host}",
                failure_threshold=self.config.circuit_failure_threshold,
                timeout_seconds=self.config.circuit_timeout_seconds,
                success_threshold=self.config.circuit_success_threshold
            )
        return self._circuit_breakers[host]
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            self._connector = TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections_per_host,
                timeout=self.config.connection_timeout,
                enable_cleanup_closed=True,
                keepalive_timeout=self.config.keepalive_timeout
            )
            timeout = ClientTimeout(total=self.config.default_timeout)
            self._session = ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers=self.config.default_headers
            )
    
    def _build_url(self, url: str) -> str:
        """Build full URL from base URL and path."""
        if self.config.base_url:
            return urljoin(self.config.base_url.rstrip("/") + "/", url.lstrip("/"))
        return url
    
    def _build_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Merge default and request params."""
        merged = {**self.config.default_params, **params}
        return {k: v for k, v in merged.items() if v is not None}
    
    def _parse_response_body(self, body: Any, headers: Dict[str, str]):
        """Parse response body based on -> Any content type."""
        content_type = headers.get("Content-Type", "").lower()
        
        if isinstance(body, bytes):
            if "application/json" in content_type:
                try:
                    return json.loads(body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return body
            elif "text/" in content_type:
                try:
                    return body.decode("utf-8")
                except UnicodeDecodeError:
                    return body.decode("latin-1")
        return body
    
    async def _execute_request(
        self,
        request: HttpRequest
    ) -> HttpResponse:
        """
        Execute a single HTTP request.
        
        Args:
            request: HTTP request configuration
            
        Returns:
            HTTP response wrapper
        """
        await self._ensure_session()
        
        start_time = time.time()
        url = self._build_url(request.url)
        params = self._build_params(request.params)
        
        # Build headers with defaults
        headers = {**self.config.default_headers, **request.headers}
        
        # Prepare request data
        json_data = request.json_data
        data = request.data
        
        if json_data is not None and not isinstance(json_data, str):
            json_data = json.dumps(json_data)
        
        # Get host for circuit breaker
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        
        async def do_request():
            """Perform the actual HTTP request."""
            timeout = ClientTimeout(total=request.timeout)
            async with self._session.request(
                method=request.method.value,
                url=url,
                params=params,
                headers=headers,
                data=data,
                json=json_data if json_data else None,
                timeout=timeout,
                allow_redirects=request.follow_redirects
            ) as response:
                # Read response body
                body = await response.read()
                elapsed = time.time() - start_time
                
                # Parse headers
                response_headers = dict(response.headers)
                
                # Parse body
                parsed_body = self._parse_response_body(body, response_headers)
                
                # Get response text
                text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
                
                return HttpResponse(
                    status_code=response.status,
                    headers=response_headers,
                    body=parsed_body,
                    text=text,
                    json=parsed_body if isinstance(parsed_body, (dict, list)) else None,
                    url=str(response.url),
                    method=request.method.value,
                    elapsed_time=elapsed,
                    request=request
                )
        
        # Circuit breaker check
        if request.use_circuit_breaker and self.config.enableCircuitBreaker:
            circuit = await self._get_circuit_breaker(host)
            if circuit.state == CircuitState.OPEN:
                raise CircuitError(
                    f"Circuit breaker is open for {host}",
                    status_code=503
                )
            
            try:
                result = await circuit.call(do_request)
                return result
            except CircuitError:
                raise
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise
        
        # Retry logic for retryable errors
        if request.allow_retries:
            retry_policy = RetryPolicy(
                max_retries=request.retry_count,
                base_delay=request.retry_backoff,
                max_delay=request.retry_max_backoff,
                retry_on_statuses=[
                    429, 500, 502, 503, 504
                ]
            )
            
            async def retry_request():
                """Execute request with retry logic."""
                return await do_request()
            
            try:
                result = await retry_policy.execute(retry_request)
                return result
            except RetryableError:
                raise HttpError(
                    "Request failed after retries",
                    request_url=url,
                    request_method=request.method.value
                )
        
        return await do_request()
    
    async def request(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        **kwargs
    ) -> HttpResponse:
        """
        Make an HTTP request.
        
        Args:
            url: Request URL or path
            method: HTTP method
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        request = HttpRequest(
            url=url,
            method=method,
            **kwargs
        )
        return await self._execute_request(request)
    
    async def get(self, url: str, **kwargs) -> HttpResponse:
        """
        Make a GET request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.GET, **kwargs)
    
    async def post(self, url: str, **kwargs) -> HttpResponse:
        """
        Make a POST request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.POST, **kwargs)
    
    async def put(self, url: str, **kwargs) -> HttpResponse:
        """
        Make a PUT request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.PUT, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> HttpResponse:
        """
        Make a PATCH request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.PATCH, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> HttpResponse:
        """
        Make a DELETE request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.DELETE, **kwargs)
    
    async def head(self, url: str, **kwargs) -> HttpResponse:
        """
        Make a HEAD request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.HEAD, **kwargs)
    
    async def options(self, url: str, **kwargs) -> HttpResponse:
        """
        Make an OPTIONS request.
        
        Args:
            url: Request URL
            **kwargs: Additional request options
            
        Returns:
            HTTP response wrapper
        """
        return await self.request(url, HttpMethod.OPTIONS, **kwargs)
    
    async def close(self):
        """Close the HTTP client and release resources."""
        async with self._lock:
            if self._closed:
                return
            
            self._closed = True
            
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
            
            if self._connector:
                await self._connector.close()
                self._connector = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        return False
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if not self._closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass


# Convenience function for quick requests
async def quick_get(url: str, **kwargs) -> HttpResponse:
    """
    Quick GET request with default settings.
    
    Args:
        url: Request URL
        **kwargs: Additional request options
        
    Returns:
        HTTP response wrapper
    """
    async with HttpClient() as client:
        return await client.get(url, **kwargs)


async def quick_post(url: str, **kwargs) -> HttpResponse:
    """
    Quick POST request with default settings.
    
    Args:
        url: Request URL
        **kwargs: Additional request options
        
    Returns:
        HTTP response wrapper
    """
    async with HttpClient() as client:
        return await client.post(url, **kwargs)
