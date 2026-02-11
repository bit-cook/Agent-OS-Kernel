# -*- coding: utf-8 -*-
"""
API Gateway Module - Agent-OS-Kernel API网关模块

提供请求路由、速率限制、认证中间件和请求/响应转换功能。
"""

from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from datetime import timezone, timedelta
import time
import re
import hashlib
import json
from collections import defaultdict
from functools import wraps
import threading


class HTTPMethod(Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    ALL = "*"


class GatewayError(Exception):
    """网关错误基类"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "GATEWAY_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class RouteNotFoundError(GatewayError):
    """路由未找到错误"""
    def __init__(self, path: str, method: str):
        super().__init__(
            message=f"Route not found: {method} {path}",
            status_code=404,
            error_code="ROUTE_NOT_FOUND"
        )


class RateLimitExceededError(GatewayError):
    """速率限制超限错误"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )
        self.retry_after = retry_after


class UnauthorizedError(GatewayError):
    """未授权错误"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED"
        )


class ForbiddenError(GatewayError):
    """禁止访问错误"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN"
        )


@dataclass
class Route:
    """路由配置"""
    path: str
    methods: List[HTTPMethod]
    handler: Callable
    middleware: List[Callable] = field(default_factory=list)
    authentication_required: bool = False
    rate_limit: Optional[Tuple[int, int]] = None  # (requests, seconds)
    roles: List[str] = field(default_factory=list)
    
    def match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        """检查路径是否匹配，返回路径参数"""
        # 处理通配符
        if self.path == "/*":
            return {}
        
        # 转换路径模式为正则表达式
        pattern = re.compile(self.path.replace("{param}", r"(?P<param>[^/]+)"))
        match = pattern.match(path)
        
        if match and method in [m.value for m in self.methods]:
            return match.groupdict()
        
        return None


@dataclass
class Request:
    """HTTP请求"""
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Optional[Any] = None
    body_raw: Optional[bytes] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    client_ip: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def get_header(self, name: str, default: str = "") -> str:
        """获取请求头"""
        return self.headers.get(name.lower(), default)
    
    def get_query(self, name: str, default: str = "") -> str:
        """获取查询参数"""
        return self.query_params.get(name, default)


@dataclass
class Response:
    """HTTP响应"""
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    body_raw: Optional[bytes] = None
    
    def set_header(self, name: str, value: str) -> None:
        """设置响应头"""
        self.headers[name.lower()] = value
    
    def get_header(self, name: str, default: str = "") -> str:
        """获取响应头"""
        return self.headers.get(name.lower(), default)


class Middleware:
    """中间件基类"""
    
    def before_request(self, request: Request, context: Dict[str, Any]) -> Optional[Response]:
        """请求前处理，返回None继续，返回Response则短路"""
        return None
    
    def after_response(self, request: Request, response: Response, context: Dict[str, Any]) -> Response:
        """响应后处理"""
        return response


class AuthenticationMiddleware(Middleware):
    """认证中间件"""
    
    def __init__(self, secret_key: str = "default-secret", algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_blacklist = set()
        self.token_expiry = {}
    
    def before_request(self, request: Request, context: Dict[str, Any]) -> Optional[Response]:
        """验证认证令牌"""
        auth_header = request.get_header("Authorization", "")
        
        if not auth_header:
            # 检查是否需要认证（由路由配置决定）
            if context.get("require_auth", False):
                return UnauthorizedError("Missing Authorization header")
            return None
        
        try:
            token = auth_header.replace("Bearer ", "")
            
            # 检查令牌是否在黑名单中
            if token in self.token_blacklist:
                return UnauthorizedError("Token revoked")
            
            # 验证令牌（简化版本，实际应使用JWT）
            payload = self._decode_token(token)
            
            if payload is None:
                return UnauthorizedError("Invalid token")
            
            # 检查令牌是否过期
            if payload.get("exp") and datetime.fromtimestamp(payload["exp"]) < datetime.now(timezone.utc):
                return UnauthorizedError("Token expired")
            
            # 将用户信息添加到请求上下文
            context["user"] = payload.get("sub")
            context["user_id"] = payload.get("user_id")
            context["roles"] = payload.get("roles", [])
            context["token"] = token
            
            return None
            
        except Exception as e:
            return UnauthorizedError(f"Authentication failed: {str(e)}")
    
    def _decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌（简化版本）"""
        try:
            # 简单的Base64解码，实际应使用JWT库
            import base64
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload_json = base64.b64decode(payload_b64)
            return json.loads(payload_json)
        except Exception:
            return None
    
    def generate_token(self, user_id: str, roles: List[str] = None, expires_in: int = 3600) -> str:
        """生成令牌"""
        import base64
        import hmac
        import hashlib
        
        header = {"alg": self.algorithm, "typ": "JWT"}
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "roles": roles or [],
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        
        signature = hmac.new(
            self.secret_key.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{header_b64}.{payload_b64}.{signature}"
    
    def revoke_token(self, token: str) -> None:
        """撤销令牌"""
        self.token_blacklist.add(token)
    
    def check_role(self, context: Dict[str, Any], required_role: str) -> bool:
        """检查用户角色"""
        user_roles = context.get("roles", [])
        return required_role in user_roles


class RateLimitMiddleware(Middleware):
    """速率限制中间件"""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def before_request(self, request: Request, context: Dict[str, Any]) -> Optional[Response]:
        """检查速率限制"""
        rate_limit = context.get("rate_limit")
        
        if rate_limit is None:
            return None
        
        max_requests, window_seconds = rate_limit
        client_id = self._get_client_id(request)
        
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)
        
        with self.lock:
            # 清理过期请求记录
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > window_start
            ]
            
            # 检查是否超限
            if len(self.requests[client_id]) >= max_requests:
                oldest = min(self.requests[client_id])
                retry_after = int((oldest + timedelta(seconds=window_seconds) - now).total_seconds())
                
                response = Response(
                    status_code=429,
                    body={"error": "Rate limit exceeded", "retry_after": max(retry_after, 1)}
                )
                response.set_header("Retry-After", str(max(retry_after, 1)))
                response.set_header("X-RateLimit-Limit", str(max_requests))
                response.set_header("X-RateLimit-Remaining", "0")
                
                return response
            
            # 记录请求
            self.requests[client_id].append(now)
            
            # 更新上下文中的限制信息
            context["rate_limit_remaining"] = max_requests - len(self.requests[client_id])
            
            return None
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端ID"""
        # 优先使用X-Forwarded-For头（代理场景）
        forwarded_for = request.get_header("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # 使用真实IP
        return request.client_ip or request.get_header("X-Real-IP", "unknown")


class RequestTransformMiddleware(Middleware):
    """请求转换中间件"""
    
    def __init__(self):
        self.transformers: List[Callable[[Request], Request]] = []
    
    def add_transformer(self, transformer: Callable[[Request], Request]) -> None:
        """添加请求转换器"""
        self.transformers.append(transformer)
    
    def before_request(self, request: Request, context: Dict[str, Any]) -> Optional[Response]:
        """应用请求转换"""
        for transformer in self.transformers:
            request = transformer(request)
        return None
    
    def transform_json_body(self, request: Request) -> Request:
        """将JSON body字符串转换为对象"""
        if request.body_raw and isinstance(request.body_raw, bytes):
            try:
                request.body = json.loads(request.body_raw.decode("utf-8"))
            except json.JSONDecodeError:
                request.body = None
        return request
    
    def transform_query_params(self, request: Request) -> Request:
        """转换查询参数类型"""
        # 转换数值类型的查询参数
        for key, value in request.query_params.items():
            if value.isdigit():
                request.query_params[key] = int(value)
            else:
                try:
                    request.query_params[key] = float(value)
                except ValueError:
                    pass
        return request
    
    def transform_headers(self, request: Request) -> Request:
        """标准化请求头"""
        # 将所有请求头转换为小写
        request.headers = {k.lower(): v for k, v in request.headers.items()}
        return request


class ResponseTransformMiddleware(Middleware):
    """响应转换中间件"""
    
    def __init__(self):
        self.transformers: List[Callable[[Response], Response]] = []
    
    def add_transformer(self, transformer: Callable[[Response], Response]) -> None:
        """添加响应转换器"""
        self.transformers.append(transformer)
    
    def after_response(self, request: Request, response: Response, context: Dict[str, Any]) -> Response:
        """应用响应转换"""
        for transformer in self.transformers:
            response = transformer(response)
        return response
    
    def add_cors_headers(self, origin: str = "*") -> Callable[[Response], Response]:
        """添加CORS头"""
        def transformer(response: Response) -> Response:
            response.set_header("Access-Control-Allow-Origin", origin)
            response.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
            response.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            response.set_header("Access-Control-Max-Age", "86400")
            return response
        return transformer
    
    def wrap_response(self, response: Response) -> Response:
        """包装响应为标准格式"""
        if response.body is not None and not isinstance(response.body, dict):
            response.body = {"data": response.body}
        return response


class APIGateway:
    """API网关主类"""
    
    def __init__(self):
        self.routes: List[Route] = []
        self.middleware_chain: List[Middleware] = []
        self.global_middleware: List[Middleware] = []
        self.exception_handlers: Dict[type, Callable] = {}
        self._route_lock = threading.Lock()
    
    def add_route(
        self,
        path: str,
        methods: List[str],
        handler: Callable,
        middleware: List[Callable] = None,
        authentication_required: bool = False,
        rate_limit: Tuple[int, int] = None,
        roles: List[str] = None
    ) -> None:
        """添加路由"""
        with self._route_lock:
            http_methods = [HTTPMethod(m.upper()) for m in methods]
            route = Route(
                path=path,
                methods=http_methods,
                handler=handler,
                middleware=middleware or [],
                authentication_required=authentication_required,
                rate_limit=rate_limit,
                roles=roles or []
            )
            self.routes.append(route)
    
    def add_middleware(self, middleware: Middleware, position: int = None) -> None:
        """添加中间件"""
        if position is None:
            self.global_middleware.append(middleware)
        else:
            self.global_middleware.insert(position, middleware)
    
    def add_exception_handler(self, exception_type: type, handler: Callable) -> None:
        """添加异常处理器"""
        self.exception_handlers[exception_type] = handler
    
    def route(
        self,
        path: str,
        methods: List[str] = None,
        authentication_required: bool = False,
        rate_limit: Tuple[int, int] = None,
        roles: List[str] = None
    ) -> Callable:
        """路由装饰器"""
        if methods is None:
            methods = ["GET"]
        
        def decorator(handler: Callable) -> Callable:
            self.add_route(
                path=path,
                methods=methods,
                handler=handler,
                authentication_required=authentication_required,
                rate_limit=rate_limit,
                roles=roles
            )
            return handler
        
        return decorator
    
    def handle_request(self, request: Request) -> Response:
        """处理请求"""
        context = {
            "require_auth": False,
            "rate_limit": None,
            "route": None,
            "route_params": {}
        }
        
        try:
            # 1. 查找路由
            route, route_params = self._find_route(request.method, request.path)
            
            if route is None:
                raise RouteNotFoundError(request.path, request.method)
            
            context["route"] = route
            context["route_params"] = route_params
            context["require_auth"] = route.authentication_required
            
            if route.rate_limit:
                context["rate_limit"] = route.rate_limit
            
            # 2. 执行全局前置中间件
            for middleware in self.global_middleware:
                response = middleware.before_request(request, context)
                if response is not None:
                    return self._add_default_headers(response)
            
            # 3. 执行路由中间件
            for middleware in route.middleware:
                response = middleware.before_request(request, context)
                if response is not None:
                    return self._add_default_headers(response)
            
            # 4. 调用处理函数
            handler_response = route.handler(request, route_params, context)
            
            # 如果处理函数返回Response对象
            if isinstance(handler_response, Response):
                response = handler_response
            else:
                # 如果返回的是其他类型，包装成Response
                response = Response(body=handler_response)
            
            # 5. 执行路由后置中间件
            for middleware in reversed(route.middleware):
                response = middleware.after_response(request, response, context)
            
            # 6. 执行全局后置中间件
            for middleware in reversed(self.global_middleware):
                response = middleware.after_response(request, response, context)
            
            return self._add_default_headers(response)
            
        except GatewayError as e:
            return self._handle_exception(e, context)
        except Exception as e:
            # 查找异常处理器
            for exc_type, handler in self.exception_handlers.items():
                if isinstance(e, exc_type):
                    return handler(e, context)
            
            # 默认异常处理
            return Response(
                status_code=500,
                body={"error": "Internal server error", "message": str(e)}
            )
    
    def _find_route(self, method: str, path: str) -> Tuple[Optional[Route], Dict[str, str]]:
        """查找路由"""
        for route in self.routes:
            route_params = route.match(method, path)
            if route_params is not None:
                return route, route_params
        return None, {}
    
    def _handle_exception(self, error: GatewayError, context: Dict[str, Any]) -> Response:
        """处理网关异常"""
        response = Response(
            status_code=error.status_code,
            body={"error": error.error_code, "message": error.message}
        )
        
        if isinstance(error, RateLimitExceededError):
            response.set_header("Retry-After", str(error.retry_after))
        
        return self._add_default_headers(response)
    
    def _add_default_headers(self, response: Response) -> Response:
        """添加默认响应头"""
        if "X-Content-Type-Options" not in response.headers:
            response.set_header("X-Content-Type-Options", "nosniff")
        if "X-Frame-Options" not in response.headers:
            response.set_header("X-Frame-Options", "DENY")
        return response
    
    def get_registered_routes(self) -> List[Dict[str, Any]]:
        """获取所有注册路由"""
        return [
            {
                "path": route.path,
                "methods": [m.value for m in route.methods],
                "authentication_required": route.authentication_required,
                "rate_limit": route.rate_limit,
                "roles": route.roles
            }
            for route in self.routes
        ]


# 工厂函数
def create_api_gateway() -> APIGateway:
    """创建API网关实例"""
    return APIGateway()


def create_auth_middleware(secret_key: str = "default-secret", algorithm: str = "HS256") -> AuthenticationMiddleware:
    """创建认证中间件"""
    return AuthenticationMiddleware(secret_key=secret_key, algorithm=algorithm)


def create_rate_limit_middleware() -> RateLimitMiddleware:
    """创建速率限制中间件"""
    return RateLimitMiddleware()


def create_transform_middleware() -> RequestTransformMiddleware:
    """创建请求转换中间件"""
    return RequestTransformMiddleware()
