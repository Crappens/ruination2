class ObjectNotFoundException(Exception):
    pass


class DeleteInvalidObjectException(Exception):
    pass


class InvalidObjectException(Exception):
    pass


class InvalidParameterException(Exception):
    pass


class InvalidObjectType(Exception):
    pass

class LockingError(Exception):
    """Thrown when an operation cannot complete because pages are locked."""
