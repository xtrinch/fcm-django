from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from firebase_admin import messaging
    from firebase_admin.exceptions import FirebaseError


class FirebaseResponseDict(NamedTuple):
    # All errors are stored rather than raised in BatchResponse.exceptions
    # or TopicManagementResponse.errors
    response: messaging.BatchResponse | messaging.TopicManagementResponse
    registration_ids_sent: list[str]
    deactivated_registration_ids: list[str]

    @property
    def success_count(self) -> int:
        return getattr(
            self.response,
            "success_count",
            len(self.registration_ids_sent) - self.failure_count,
        )

    @property
    def failure_count(self) -> int:
        return getattr(
            self.response, "failure_count", len(self.failed_registration_ids)
        )

    @property
    def has_failures(self) -> bool:
        return self.failure_count > 0

    @property
    def all_failed(self) -> bool:
        return bool(self.registration_ids_sent) and (
            self.failure_count == len(self.registration_ids_sent)
        )

    @property
    def failed_registration_ids(self) -> list[str]:
        responses = getattr(self.response, "responses", None)
        if isinstance(responses, list):
            return [
                registration_id
                for send_response, registration_id in zip(
                    responses,
                    self.registration_ids_sent,
                )
                if send_response.exception
            ]
        errors = getattr(self.response, "errors", None)
        if isinstance(errors, list):
            return [
                self.registration_ids_sent[error.index]
                for error in errors
                if error.index < len(self.registration_ids_sent)
            ]
        return []

    @property
    def failed_exceptions(self) -> list[FirebaseError | str]:
        responses = getattr(self.response, "responses", None)
        if isinstance(responses, list):
            return [
                send_response.exception
                for send_response in responses
                if send_response.exception
            ]
        errors = getattr(self.response, "errors", None)
        if isinstance(errors, list):
            return [error.reason for error in errors]
        return []

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "has_failures": self.has_failures,
            "all_failed": self.all_failed,
            "registration_ids_sent": self.registration_ids_sent,
            "failed_registration_ids": self.failed_registration_ids,
            "deactivated_registration_ids": self.deactivated_registration_ids,
            "failed_exceptions": self.failed_exceptions,
        }


class DeviceDeactivationData(NamedTuple):
    registration_id: str
    device_id: Any
    user_id: Any
