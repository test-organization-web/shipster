class PrivacyExportNotFoundError(Exception):
    pass


class PrivacyExportSubjectNotFoundError(Exception):
    pass


class PrivacyExportNotReadyError(Exception):
    pass


class PrivacyExportAccessDeniedError(Exception):
    pass


class PrivacyExportFailedError(Exception):
    pass


class PrivacyExportExpiredError(Exception):
    pass


class PrivacyErasureNotFoundError(Exception):
    pass


class PrivacyErasureSubjectNotFoundError(Exception):
    pass


class PrivacyErasureConflictError(Exception):
    """Another erasure request is already pending or processing for this subject."""
