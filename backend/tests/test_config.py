from app.config import Settings


def test_cors_origins_accept_comma_separated_environment_format():
    settings = Settings(
        _env_file=None,
        cors_origins="http://localhost:5173, http://localhost:8080",
    )

    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:8080"]


def test_cors_origins_accept_json_list_environment_format():
    settings = Settings(
        _env_file=None,
        cors_origins='["https://analyst.example", "https://review.example"]',
    )

    assert settings.cors_origins == ["https://analyst.example", "https://review.example"]
