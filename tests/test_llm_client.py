import os
import unittest
from unittest.mock import patch

from modules.llm_client import (
    LLMUnavailableError,
    call_llm,
    get_config_value,
    get_model_for_provider,
    get_provider_status,
    parse_json_response,
)


class LLMClientTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_fails_without_network_call(self):
        with self.assertRaises(LLMUnavailableError):
            call_llm("gemini", "system", "user")

    @patch("modules.llm_client._call_provider")
    @patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "bad-gemini",
            "OPENROUTER_API_KEY": "bad-openrouter",
            "GROQ_API_KEY": "working-groq",
        },
        clear=True,
    )
    def test_auto_tries_providers_in_order(self, mock_call):
        mock_call.side_effect = [
            LLMUnavailableError("gemini failed"),
            LLMUnavailableError("openrouter failed"),
            "groq response",
        ]

        result = call_llm("auto", "system", "user")

        self.assertEqual(result, "groq response")
        self.assertEqual(
            [call.args[0] for call in mock_call.call_args_list],
            ["gemini", "openrouter", "groq"],
        )

    def test_parses_json_inside_code_fence_and_rejects_plain_text(self):
        parsed = parse_json_response('```json\n{"question": "为什么？"}\n```')
        self.assertEqual(parsed["question"], "为什么？")
        self.assertIsNone(parse_json_response("这不是 JSON"))

    @patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "secret-value",
            "DEFAULT_PROVIDER": "groq",
            "GROQ_MODEL": "custom-model",
        },
        clear=True,
    )
    def test_status_never_returns_key_value(self):
        status = get_provider_status()

        self.assertEqual(status["gemini"], True)
        self.assertEqual(status["openrouter"], False)
        self.assertNotIn("secret-value", repr(status))
        self.assertEqual(get_model_for_provider("groq"), "custom-model")

    @patch("modules.llm_client._get_streamlit_secret")
    @patch.dict(os.environ, {}, clear=True)
    def test_reads_streamlit_cloud_secret_when_env_is_missing(self, mock_secret):
        mock_secret.side_effect = lambda name: {
            "OPENROUTER_API_KEY": "cloud-secret",
            "DEFAULT_PROVIDER": "openrouter",
            "OPENROUTER_MODEL": "openrouter/free",
        }.get(name)

        self.assertEqual(get_config_value("OPENROUTER_API_KEY"), "cloud-secret")
        self.assertTrue(get_provider_status()["openrouter"])
        self.assertEqual(get_model_for_provider("openrouter"), "openrouter/free")


if __name__ == "__main__":
    unittest.main()
