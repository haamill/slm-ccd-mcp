class LabError(RuntimeError):
    def __init__(self, code, message, *, stage='validate', hardware_submitted=False, details=None):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.hardware_submitted = hardware_submitted
        self.details = details or {}

    def to_dict(self):
        return {'code': self.code, 'message': str(self), 'stage': self.stage,
                'hardware_submitted': self.hardware_submitted, 'details': self.details}
