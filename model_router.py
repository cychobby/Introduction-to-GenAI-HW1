import re
from typing import Tuple, Optional

class ModelRouter:
    def __init__(self):
        # Model capabilities
        self.models = {
            "groq": {
                "llama-3.3-70b-versatile": {"vision": False, "complexity": "high", "speed": "medium"},
                "meta-llama/llama-4-scout-17b-16e-instruct": {"vision": True, "complexity": "high", "speed": "medium"}
            },
            "nvidia": {
                "GPT-OSS-120b": {"vision": False, "complexity": "high", "speed": "medium"}
            }
        }

    def analyze_input(self, prompt: str, has_image: bool = False, api_source: Optional[str] = None) -> Tuple[str, str]:
        """
        Analyze user input and return recommended model and reason
        Returns: (model_name, reason)
        """
        task_type = self.detect_task_type(prompt)
        complexity = self.estimate_complexity(prompt)

        # Auto-routing only supports the configured provider models
        if api_source == "groq":
            if has_image:
                return "meta-llama/llama-4-scout-17b-16e-instruct"
            return "llama-3.3-70b-versatile"
        if api_source == "nvidia":
            return "GPT-OSS-120b"

        # Fallback for generic selection
        if has_image:
            return self.select_vision_model(task_type, complexity)

        return self.select_model(task_type, complexity)

    def detect_task_type(self, prompt: str) -> str:
        """Detect the type of task from the prompt"""
        prompt_lower = prompt.lower()

        # Coding tasks
        coding_keywords = ["code", "programming", "debug", "algorithm", "function", "class", "script", "python", "javascript", "java", "c++", "html", "css"]
        if any(keyword in prompt_lower for keyword in coding_keywords):
            return "coding"

        # Analysis tasks
        analysis_keywords = ["analyze", "explain", "compare", "evaluate", "review", "summarize", "research"]
        if any(keyword in prompt_lower for keyword in analysis_keywords):
            return "analysis"

        # Creative tasks
        creative_keywords = ["write", "create", "story", "poem", "design", "imagine", "generate"]
        if any(keyword in prompt_lower for keyword in creative_keywords):
            return "creative"

        # Math/calculation tasks
        math_keywords = ["calculate", "math", "equation", "solve", "formula", "+", "-", "*", "/"]
        if any(keyword in prompt_lower for keyword in math_keywords):
            return "math"

        return "general"

    def estimate_complexity(self, prompt: str) -> str:
        """Estimate the complexity of the task"""
        word_count = len(prompt.split())

        # Complex indicators
        complex_indicators = ["explain", "why", "how", "analyze", "compare", "research", "detailed"]
        has_complex_words = any(word in prompt.lower() for word in complex_indicators)

        if word_count > 100 or has_complex_words:
            return "high"
        elif word_count > 50:
            return "medium"
        else:
            return "low"

    def select_model(self, task_type: str, complexity: str) -> Tuple[str, str]:
        """Select the best model for the task"""
        return "llama-3.3-70b-versatile", "使用唯一可用的 Groq 模型"

    def select_vision_model(self, task_type: str, complexity: str) -> Tuple[str, str]:
        """Select the best vision-capable model"""
        return "llama-3.3-70b-versatile", "使用唯一可用的 Groq 模型（目前無專用視覺模型）"

    def get_available_models(self, api_source: str) -> list:
        """Get list of available models for an API source"""
        return list(self.models.get(api_source, {}).keys())

    def is_vision_supported(self, model_name: str, api_source: str) -> bool:
        """Check if a model supports vision"""
        model_info = self.models.get(api_source, {}).get(model_name, {})
        return model_info.get("vision", False)#</content>
#<parameter name="filePath">/home/daddywu/Python區/GenAI_class/model_router.py