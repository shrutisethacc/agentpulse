"""
DeepEval judge for local Ollama models.

DeepEval 4.0.2 ships a native OllamaModel at deepeval.models.llms.ollama_model.
This module re-exports it under the name OllamaJudge so the rest of the codebase
doesn't need to change import paths.

To configure the model globally (saves to .env.local):
    .venv\\Scripts\\deepeval.exe set-ollama -m llama3.2:3b -u http://localhost:11434 --save
"""

from deepeval.models.llms.ollama_model import OllamaModel as OllamaJudge

__all__ = ["OllamaJudge"]
