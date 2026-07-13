"""Move Hermes — 全局异常处理器 + 统一错误格式"""
import logging
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger("move-hermes")


class AppException(Exception):
    """应用自定义异常基类"""
    def __init__(self, message: str, code: int = 400, detail: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail or {}


class ResourceNotFoundException(AppException):
    """资源未找到"""
    def __init__(self, resource: str, id=None):
        msg = f"{resource} not found"
        if id is not None:
            msg += f" (id={id})"
        super().__init__(msg, code=404)


class BusinessRuleException(AppException):
    """业务规则违反"""
    def __init__(self, message: str):
        super().__init__(message, code=422)


async def app_exception_handler(request: Request, exc: AppException):
    """处理自定义应用异常"""
    logger.warning(f"[AppError] {exc.message} | {request.url.path}")
    return JSONResponse(
        status_code=exc.code,
        content={
            "success": False,
            "error": exc.message,
            "code": exc.code,
            **exc.detail
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理Pydantic/请求验证异常"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"[ValidationError] {exc.body} | {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "请求参数验证失败",
            "code": 422,
            "errors": errors
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理FastAPI HTTP异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "code": exc.status_code
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    error_id = id(exc)
    logger.error(
        f"[InternalServerError] {type(exc).__name__}: {exc}\n"
        f"  Path: {request.url.path}\n"
        f"  Method: {request.method}\n"
        f"  Traceback:\n{traceback.format_exc()}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "code": 500,
            "error_id": error_id  # 用于日志追踪
        }
    )


def register_exception_handlers(app):
    """注册所有异常处理器到FastAPI应用"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    return app
