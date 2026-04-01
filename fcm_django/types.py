from typing import Any, NamedTuple


class DeviceDeactivationData(NamedTuple):
    registration_id: str
    device_id: Any
    user_id: Any
