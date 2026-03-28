class ServiceError(Exception):
    status = 400
    default_message = "Bad request"

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(ServiceError):
    status = 404
    default_message = "Not found"


class AuthenticationError(ServiceError):
    status = 401
    default_message = "Invalid credentials"


class ForbiddenError(ServiceError):
    status = 403
    default_message = "Access denied"


class ValidationError(ServiceError):
    status = 422
    default_message = "Validation failed"

    def __init__(self, message=None, errors=None):
        self.errors = errors
        super().__init__(message)
