from typing import Any,Optional

class DomainError(Exception):
    code: str = "DOMAIN_ERROR"
    http_status: int = 500

    def __init__(
            self,
            message: str,
            code: Optional[str] = None,
            details: Optional[dict[str, Any]] = None,
            http_status: Optional[int] = None,
            ) -> None:

        super().__init__(message)
        self.message = message

        if code is not None:
            self.code = code

        self.details = details if details is not None else {}

        if http_status is not None:
            self.http_status = http_status


    def to_dict(self) -> dict[str, Any]:
        return {
            "code" : self.code,
            "message" : self.message,
            "details" : self.details,
        }


class AuthenticationError(Exception):
    code: str = "AUTHENTICATION_ERROR"
    http_status: int = 401

    def __init__(
            self,
            message: str = "Authentication required",
            details: Optional[dict[str, Any]] = None,
    ) -> None:

        super.__init__(
            message = message,
            code = self.code,
            details = details,
            http_status = self.http_status,
        )

class PermissionDenied(Exception):
    code: str = "PERMISSION_DENIED"
    http_status: int = 403

    def __init__(
            self,
            message : str = "Permission Denied",
            details: Optional[dict[str, Any]] = None,
    ) -> None:

        super.__init__(
            message = message,
            code = self.code,
            details = details,
            http_status = self.http_status
        )

class NotFoundError(Exception):
    code: str = "NOT_FOUND"
    http_status: int = 404

    def __init__(
            self,
            message : str = "Not Found",
            details: Optional[dict[str, Any]] = None,
    ) -> None:

        super.__init__(
            message = message,
            code = self.code,
            details = details,
            http_status = self.http_status
        )

class InvalidStateError(Exception):
    code: str = "INVALID_STATE"
    http_status: int = 409

    def __init__(
            self,
            message : str = "Invalid State",
            details: Optional[dict[str, Any]] = None,
    ) -> None:

        super.__init__(
            message = message,
            code = self.code,
            details = details,
            http_satus = self.http_status
        )

class ValidationFailure(Exception):
    code: str = "VALIDATION_FAILED"
    http_status: int = 422

    def __init__(
            self,
            message : str = "Validation Failed",
            details: Optional[dict[str, Any]] = None,
    ) -> None:
        super.__init__(
            message = message,
            code = self.code,
            details = details,
            http_status = self.http_status
        )

class GateKeeperViolation(Exception):
    code: str = "GATEKEEPER_BLOCKED"
    http_status: int = 422

    def __init__()
