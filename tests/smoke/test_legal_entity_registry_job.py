from app.jobs.update_company_legal_data import (
    RegistryJobConfig,
    RegistryJobResult,
    _non_negative_float,
    _positive_int,
)


def test_positive_integer_configuration() -> None:
    assert (
        _positive_int(
            "25",
            default=100,
            maximum=1000,
        )
        == 25
    )

    assert (
        _positive_int(
            "-1",
            default=100,
            maximum=1000,
        )
        == 100
    )

    assert (
        _positive_int(
            "9999",
            default=100,
            maximum=1000,
        )
        == 1000
    )


def test_non_negative_float_configuration() -> None:
    assert (
        _non_negative_float(
            "1.5",
            default=1.0,
            maximum=60.0,
        )
        == 1.5
    )

    assert (
        _non_negative_float(
            "-1",
            default=1.0,
            maximum=60.0,
        )
        == 1.0
    )


def test_job_result_success_status() -> None:
    result = RegistryJobResult(
        selected=2,
        updated=2,
    )

    assert result.successful is True

    result.failed = 1

    assert result.successful is False


def test_job_configuration_is_bounded(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DADATA_SYNC_BATCH_SIZE",
        "5000",
    )
    monkeypatch.setenv(
        "DADATA_SYNC_RETRY_ATTEMPTS",
        "100",
    )
    monkeypatch.setenv(
        "DADATA_SYNC_REQUEST_DELAY_SECONDS",
        "1000",
    )
    monkeypatch.setenv(
        "DADATA_SYNC_RETRY_DELAY_SECONDS",
        "1000",
    )

    config = RegistryJobConfig.from_environment()

    assert config.batch_size == 1000
    assert config.retry_attempts == 10
    assert config.request_delay_seconds == 60.0
    assert config.retry_delay_seconds == 300.0
