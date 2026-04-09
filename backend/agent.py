import os
import json
import time
import logging
from typing import List, Dict, Any, Generator, Optional
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from tools import search_modules, NUSModsClient, check_prerequisites

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System Prompt
SYSTEM_PROMPT = """
You are the NUS Course Selection Agent. Your goal is to help students find the best courses based on their academic goals, preferences, and constraints.

Capabilities:
1. Search for modules based on interests or requirements.
2. Check prerequisites for modules.
3. Analyze workload and teaching styles.
4. Recommend courses that balance GPA goals and intellectual interest.

Student Profile:
- Taken Modules: {taken_modules}
- Priorities: {priorities} (e.g., Knowledge-oriented, GPA-oriented, Logistical)

When recommending:
- Be specific about why a module fits their profile.
- Warn them if they don't meet prerequisites.
- Mention workload intensity.
- Use markdown for formatting.
"""

class LLMProvider:
    def stream_chat(self, system_msg: str, user_msg: str) -> Generator[str, None, None]:
        raise NotImplementedError
    
    def test(self) -> Dict[str, Any]:
        raise NotImplementedError

class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.model = None

    def stream_chat(self, system_msg: str, user_msg: str) -> Generator[str, None, None]:
        if not self.model:
            raise ValueError("Gemini API Key not configured")
        
        response = self.model.generate_content([
            {"text": system_msg},
            {"text": user_msg}
        ], stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def test(self) -> Dict[str, Any]:
        if not self.model:
            return {"success": False, "error": "API Key missing"}
        try:
            res = self.model.generate_content("Hi")
            return {"success": True, "model": "gemini-1.5-pro"}
        except Exception as e:
            return {"success": False, "error": str(e)}

class OpenRouterProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_id = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")
        if self.api_key:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://nus-course-agent.local",
                    "X-Title": "NUS Course Agent",
                }
            )
        else:
            self.client = None

    def stream_chat(self, system_msg: str, user_msg: str) -> Generator[str, None, None]:
        if not self.client:
            raise ValueError("OpenRouter API Key not configured")
        
        # Merge system message into user message for better compatibility with free models
        combined_user_msg = f"{system_msg}\n\nUser Request: {user_msg}"

        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "user", "content": combined_user_msg}
            ],
            stream=True,
            extra_body={"reasoning": {"enabled": True}}
        )
        
        for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                # OpenRouter reasoning chunks might come in delta.reasoning
                reasoning = getattr(delta, 'reasoning', None)
                content = getattr(delta, 'content', None)
                
                if reasoning:
                    yield reasoning
                if content:
                    yield content
            elif hasattr(chunk, 'error'):
                raise ValueError(f"OpenRouter Error: {chunk.error}")

    def test(self) -> Dict[str, Any]:
        if not self.client:
            return {"success": False, "error": "API Key missing"}
        try:
            res = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return {"success": True, "model": self.model_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

class DemoProvider(LLMProvider):
    def stream_chat(self, system_msg: str, user_msg: str) -> Generator[str, None, None]:
        mock_response = f"**[Demo Mode]** Based on your request, I've analyzed the available modules. \n\n"
        mock_response += "I recommend checking out modules that align with your interest in " + user_msg[:40] + "...\n\n"
        mock_response += "1. **CS2109S**: Intro to AI and Machine Learning.\n"
        mock_response += "2. **CS2040S**: Data Structures and Algorithms.\n\n"
        mock_response += "*(Note: This is a fallback mock response because the selected LLM provider encountered an error.)*"
        
        for word in mock_response.split(" "):
            yield word + " "
            time.sleep(0.05)

    def test(self) -> Dict[str, Any]:
        return {"success": True, "model": "demo-mode"}

class CourseAgent:
    def __init__(self, taken_modules: List[str] = None, priorities: str = "balanced"):
        self.taken_modules = set(taken_modules or [])
        self.priorities = priorities
        
        self.provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()
        if self.provider_name == "openrouter":
            self.provider = OpenRouterProvider()
        else:
            self.provider = GeminiProvider()

    def test_connection(self) -> Dict[str, Any]:
        return self.provider.test()

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        # 1. Tool-grounded enrichment with better logging
        logger.info(f"Querying modules for: {user_message}")
        start_time = time.time()
        
        found_mods = search_modules(user_message, limit=5)
        logger.info(f"Search took {time.time() - start_time:.2f}s")

        enriched_results = []
        for mod in found_mods:
            details = NUSModsClient.get_module_details(mod['moduleCode'])
            if details:
                can_take = check_prerequisites(details.get('prereqTree'), self.taken_modules)
                # Truncate description to save tokens for free-tier models
                desc = details.get('description', '')
                if len(desc) > 300:
                    desc = desc[:300] + "..."

                enriched_results.append({
                    "code": mod['moduleCode'],
                    "title": mod['title'],
                    "description": desc,
                    "workload": details.get('workload', 'N/A'),
                    "can_take": can_take,
                    "prereq_text": details.get('prerequisite', 'None')
                })
        
        context = json.dumps(enriched_results, indent=2)
        system_msg = SYSTEM_PROMPT.format(taken_modules=list(self.taken_modules), priorities=self.priorities)
        prompt = f"User Request: {user_message}\n\nGround Truth Search Results:\n{context}\n\nPlease provide a recommendation."

        # 2. Execute with fallback
        try:
            logger.info(f"Streaming from provider: {self.provider_name}")
            for chunk in self.provider.stream_chat(system_msg, prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Provider Error ({type(e).__name__}): {str(e)}")
            # If we already yielded chunks, we can't easily start the DemoProvider stream from scratch within SSE
            # but we can yield the error message or the fallback
            yield f"\n\n**[Connection Error]** {str(e)}\n\n"
            for chunk in DemoProvider().stream_chat(system_msg, prompt):
                yield chunk

if __name__ == "__main__":
    agent = CourseAgent(taken_modules=["CS1010"], priorities="balanced")
    print(agent.test_connection())
