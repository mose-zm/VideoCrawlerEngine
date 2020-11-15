
from codetable import (
    PAGE_OUT_OF_RANGE,
    DATA_NOT_FOUND,
    DATA_EXISTS,
    VALIDATE_ERROR,
    UNAUTHORIZED_ERROR,
    TOKEN_EXPIRED,
    ACCESS_EXPIRED,
)
from fastapi.exceptions import RequestValidationError


class APIBaseError(Exception):
    code: int

    def __init__(self, msg, data=None):
        self.msg = msg
        self.data = data or []


class PageOutOfRange(APIBaseError):
    code = PAGE_OUT_OF_RANGE


class DataExistsError(APIBaseError):
    code = DATA_EXISTS


class DataNotFound(APIBaseError):
    code = DATA_NOT_FOUND


class ValidateError(APIBaseError):
    code = VALIDATE_ERROR


class UnauthorizedError(APIBaseError):
    code = UNAUTHORIZED_ERROR


class TokenExpired(APIBaseError):
    code = TOKEN_EXPIRED


class AccessExpired(APIBaseError):
    code = ACCESS_EXPIRED

