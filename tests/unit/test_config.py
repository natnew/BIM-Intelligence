"""Configuration validation (ADR-010, NFR-07, NFR-08; AGENTS.md §6 mandatory unit tests)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from bim_intelligence.config import ConfigurationError, LLMMode, Settings


def _error_text(exc: ValidationError) -> str:
    return " ".join(str(err["msg"]) for err in exc.errors())


class TestDefaults:
    def test_defaults_are_safe(self) -> None:
        settings = Settings()
        assert settings.llm_mode is LLMMode.OFF
        assert settings.llm_model == "muse-spark-1.3"
        assert settings.allow_contributor_models is False
        assert settings.allow_live_llm is False
        assert settings.llm_max_retries == 0
        assert settings.llm_max_input_tokens_per_call == 8_000
        assert settings.llm_max_output_tokens_per_call == 500
        assert settings.llm_max_calls_per_run == 2
        assert settings.llm_max_run_budget_usd == Decimal("0.10")
        assert settings.llm_project_budget_usd == Decimal("5.00")
        assert settings.bimi_host == "127.0.0.1"
        assert settings.allow_remote is False
        assert settings.has_api_key is False
        assert settings.llm_enabled is False

    def test_api_key_is_secret(self) -> None:
        placeholder = "LLM_0_" + "x" * 16  # low-entropy stand-in; never a real key
        settings = Settings(model_api_key=placeholder)
        assert placeholder not in repr(settings)
        assert placeholder not in str(settings.model_api_key)
        assert settings.has_api_key is True


class TestContributorModelRejection:
    @pytest.mark.parametrize("model", ["muse-spark-1.3-contributor", "muse-spark-1.2-contributor"])
    def test_contributor_id_rejected_by_default(self, model: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(llm_model=model)
        assert "Contributor-mode" in _error_text(exc_info.value)

    def test_contributor_id_allowed_with_explicit_override(self) -> None:
        settings = Settings(llm_model="muse-spark-1.3-contributor", allow_contributor_models=True)
        assert settings.llm_model.endswith("-contributor")

    @pytest.mark.parametrize("model", ["muse-spark-1.3", "muse-wonder-1.0", "muse-spark-1.1"])
    def test_standard_ids_accepted(self, model: str) -> None:
        assert Settings(llm_model=model).llm_model == model

    def test_empty_model_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Settings(llm_model="   ")

    def test_error_type_is_configuration_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(llm_model="muse-spark-1.3-contributor")
        assert any(
            isinstance(e.get("ctx", {}).get("error"), ConfigurationError)
            for e in exc_info.value.errors()
        )


class TestLiveMode:
    def test_live_mode_requires_key(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(llm_mode="live")
        assert "MODEL_API_KEY" in _error_text(exc_info.value)

    def test_live_mode_with_key(self) -> None:
        settings = Settings(
            llm_mode="live",
            allow_live_llm=True,
            model_api_key="LLM_0_" + "x" * 16,
        )
        assert settings.llm_enabled is True

    def test_replay_mode_needs_no_key(self) -> None:
        assert Settings(llm_mode="replay").llm_enabled is True

    def test_live_mode_requires_explicit_enablement(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(llm_mode="live", model_api_key="LLM_0_" + "x" * 16)
        assert "ALLOW_LIVE_LLM" in _error_text(exc_info.value)

    def test_live_mode_requires_pricing(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                llm_mode="live",
                allow_live_llm=True,
                model_api_key="LLM_0_" + "x" * 16,
                llm_price_input_per_m=None,
            )
        assert "pricing" in _error_text(exc_info.value).lower()

    def test_meta_base_url_cannot_be_overridden(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(llm_base_url="https://attacker.example/v1")
        assert "api.meta.ai" in _error_text(exc_info.value)

    def test_budget_limits_cannot_exceed_t5_caps(self) -> None:
        with pytest.raises(ValidationError):
            Settings(llm_project_budget_usd=5.01)

    def test_production_requires_the_approved_live_configuration(self) -> None:
        with pytest.raises(ValidationError, match="BIMI_ENVIRONMENT=production"):
            Settings(bimi_environment="production")

        with pytest.raises(ValidationError, match="MODEL_API_KEY"):
            Settings(bimi_environment="production", llm_mode="live", allow_live_llm=True)

        settings = Settings(
            bimi_environment="production",
            llm_mode="live",
            allow_live_llm=True,
            model_api_key="LLM_0_" + "x" * 16,
        )
        assert settings.llm_model == "muse-spark-1.3"

    def test_production_rejects_nonstandard_or_contributor_models(self) -> None:
        with pytest.raises(ValidationError, match=r"muse-spark-1\.3"):
            Settings(
                bimi_environment="production",
                llm_mode="live",
                allow_live_llm=True,
                model_api_key="LLM_0_" + "x" * 16,
                llm_model="muse-wonder-1.0",
            )

        with pytest.raises(ValidationError, match="ALLOW_CONTRIBUTOR_MODELS"):
            Settings(
                bimi_environment="production",
                llm_mode="live",
                allow_live_llm=True,
                allow_contributor_models=True,
                model_api_key="LLM_0_" + "x" * 16,
                llm_model="muse-spark-1.3-contributor",
            )


class TestRemoteBindingGuard:
    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "127.0.0.2"])
    def test_loopback_hosts_allowed(self, host: str) -> None:
        assert Settings(bimi_host=host).bimi_host == host

    @pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.internal"])
    def test_non_loopback_rejected_by_default(self, host: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(bimi_host=host)
        assert "ALLOW_REMOTE" in _error_text(exc_info.value)

    def test_non_loopback_allowed_with_flag(self) -> None:
        assert Settings(bimi_host="0.0.0.0", allow_remote=True).bimi_host == "0.0.0.0"


class TestEnvironmentParsing:
    def test_reads_environment_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_MODE", "replay")
        monkeypatch.setenv("BIMI_ENVIRONMENT", "development")
        monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
        settings = Settings()
        assert settings.llm_mode is LLMMode.REPLAY
        assert settings.bimi_environment == "development"
        assert settings.cors_origins == ["http://a.test", "http://b.test"]

    def test_contributor_rejection_applies_to_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_MODEL", "muse-spark-1.3-contributor")
        with pytest.raises(ValidationError):
            Settings()
