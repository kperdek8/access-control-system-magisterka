class SchemaMappingNotFoundError(Exception):
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        super().__init__(f"Type '{entity_type}' is not registered in Schema Registry.")


class SelfDelegationNotAllowedError(Exception):
    def __init__(self):
        super().__init__(f"User is not allowed to delegate permission to himself.")


class DurationExceededLimitError(Exception):
    def __init__(self):
        super().__init__(f"User is not allowed to delegate permission to himself.")