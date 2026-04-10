class OrderNotFoundError(Exception):
    """Raised when an order cannot be loaded by identifier."""


class OrderNumberAlreadyUsedError(Exception):
    """Raised when a new order uses an order number that already exists."""
