"""
Custom DeepEval judge using Azure OpenAI.

DeepEval's built-in AzureOpenAIModel requires the model to be registered in
its internal OPENAI_MODELS_DATA catalog. gpt-5.2-chat is not in that catalog
(it's an Accenture enterprise deployment), so we wrap the openai SDK directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI, AsyncAzureOpenAI
from deepeval.models import DeepEvalBaseLLM

load_dotenv(Path(__file__).parent.parent / ".env")


class AzureJudge(DeepEvalBaseLLM):
    def __init__(
        self,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
    ):
        self.endpoint   = (endpoint   or os.environ["AZURE_OPENAI_ENDPOINT"]).rstrip("/")
        self.deployment = deployment  or os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.api_key    = api_key     or os.environ["AZURE_OPENAI_API_KEY"]
        self.api_version = api_version or os.environ["AZURE_OPENAI_API_VERSION"]
        super().__init__(self.deployment)

    def load_model(self):
        return AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    def generate(self, prompt: str) -> str:
        client = self.load_model()
        resp = client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""

    async def a_generate(self, prompt: str) -> str:
        client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )
        resp = await client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""

    def get_model_name(self) -> str:
        return f"Azure/{self.deployment}"
