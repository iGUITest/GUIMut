class DeviceInfraError(Exception):
    """Base class for device infrastructure exceptions."""
    def __init__(self, message):
        super(Exception, self).__init__(message)
        self.message = message