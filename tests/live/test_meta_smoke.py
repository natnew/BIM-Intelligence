from __future__ import annotations

import os
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

from bim_intelligence.config import LLMMode, Settings
from bim_intelligence.llm.client import ChatMessage
from bim_intelligence.llm.errors import LLMClientError
from bim_intelligence.llm.factory import create_client


class _SmokeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["T5_SMOKE_OK"]


@pytest.mark.live
def test_meta_muse_spark_structured_output_smoke(request: pytest.FixtureRequest) -> None:
    if request.config.getoption("markexpr") != "live":
        pytest.skip("Invoke this named test with `-m live` after per-session owner approval.")
    if os.environ.get("BIMI_LIVE_LLM") != "1":
        pytest.skip("BIMI_LIVE_LLM=1 is required for the explicitly approved smoke test.")
    if os.environ.get("BIMI_LIVE_APPROVAL") != "T5-META-MUSE-SPARK-SMOKE":
        pytest.skip("The per-session T-5 smoke-test approval token is required.")

    settings = Settings()
    if settings.llm_mode is not LLMMode.LIVE or not settings.allow_live_llm:
        pytest.fail("LLM_MODE=live and ALLOW_LIVE_LLM=true are required; no request was sent.")
    client = create_client(settings)
    if client is None:
        pytest.fail("Live client configuration was not established; no request was sent.")
    try:
        completion = client.complete(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "Return exactly one JSON object with status set to T5_SMOKE_OK. "
                        "Do not include any other fields or text."
                    ),
                ),
                ChatMessage(role="user", content="Confirm structured-output connectivity."),
            ],
            response_model=_SmokeResponse,
            max_output_tokens=settings.llm_max_output_tokens_per_call,
            purpose="t5_smoke",
            run_id="T5-META-MUSE-SPARK-SMOKE",
        )
    except LLMClientError:
        pytest.fail(
            "The explicitly approved Meta smoke request failed; provider details were suppressed."
        )
    if completion.value.status != "T5_SMOKE_OK" or completion.model != settings.llm_model:
        pytest.fail("Meta response did not satisfy the structured-output smoke criteria.")
