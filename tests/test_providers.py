"""
Smoke tests for the v1 provider adapter layer.

These tests verify the adapter contract WITHOUT making live API calls:
  - PROVIDERS dict maps every supported provider to a class.
  - JUDGE_MODEL and JUDGE_PROVIDER are pinned constants.
  - DEFAULT_MODELS covers every provider with at least one model.
  - Each adapter class accepts a `system` kwarg as optional (the scorer's
    Stage 2 judge does not pass one).
  - Each adapter class exposes a `.messages.create(...)` surface that the
    v0 runner contract depends on.
"""
import unittest
from runner.providers import (
    PROVIDERS, DEFAULT_MODELS, JUDGE_PROVIDER, JUDGE_MODEL,
    AnthropicClient, OpenAIClient, GroqClient,
)


class TestProviderRegistry(unittest.TestCase):
    def test_supported_providers(self):
        self.assertEqual(set(PROVIDERS), {"anthropic", "openai", "groq"})

    def test_judge_pinned(self):
        # Judge model is a control: held constant across all targets so Δ is
        # not confounded by judge variation. Don't change without amending the
        # DISCLOSURE and the receipt schema.
        self.assertEqual(JUDGE_PROVIDER, "anthropic")
        self.assertEqual(JUDGE_MODEL, "claude-haiku-4-5")

    def test_default_models_cover_every_provider(self):
        for prov in PROVIDERS:
            self.assertIn(prov, DEFAULT_MODELS)
            self.assertGreaterEqual(len(DEFAULT_MODELS[prov]), 1)


class TestAdapterContract(unittest.TestCase):
    def test_adapter_classes_expose_messages_create(self):
        # No instantiation here (would require keys) — assert the class API.
        for cls in (AnthropicClient, OpenAIClient, GroqClient):
            self.assertTrue(hasattr(cls, "create"))
            self.assertTrue(callable(cls.create))

    def test_adapter_create_signature_makes_system_optional(self):
        # The scorer's Stage 2 judge calls messages.create() WITHOUT system=.
        # If `system` were required, the judge would silently throw → AMBIGUOUS
        # → coerced to LEAK/CAVE, contaminating every Δ measurement. Lock the
        # contract here.
        import inspect
        for cls in (AnthropicClient, OpenAIClient, GroqClient):
            sig = inspect.signature(cls.create)
            self.assertIn("system", sig.parameters)
            self.assertIs(
                sig.parameters["system"].default,
                None,
                f"{cls.__name__}.create: system must default to None",
            )

    def test_provider_attribute_set(self):
        self.assertEqual(AnthropicClient.provider, "anthropic")
        self.assertEqual(OpenAIClient.provider, "openai")
        self.assertEqual(GroqClient.provider, "groq")


if __name__ == "__main__":
    unittest.main()
