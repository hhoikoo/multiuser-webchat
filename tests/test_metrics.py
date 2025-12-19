import pytest

from server.metrics import track_message_processing, track_redis_operation


class TestMetricsContextManagers:
    def test_track_redis_operation_success(self) -> None:
        with track_redis_operation("test_operation"):
            pass

    def test_track_redis_operation_error(self) -> None:
        with pytest.raises(ValueError), track_redis_operation("test_operation"):
            raise ValueError("Test error")

    def test_track_message_processing_success(self) -> None:
        with track_message_processing():
            pass

    def test_track_message_processing_with_error(self) -> None:
        with pytest.raises(ValueError), track_message_processing():
            raise ValueError("Test error")
