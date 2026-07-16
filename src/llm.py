"""
llm.py

Connects to Gemini 2.5 Flash via the Google Gen AI SDK.
Defines the four tools Rover can use and the system prompt.
"""
from google import genai
from google.genai import types
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import re
import logging

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# Logger for LLM decisions
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger('rover.llm')


class NormalizedResponse:
    """Simple wrapper used to normalize responses from different providers."""
    def __init__(self, text='', function_calls=None, candidates=None):
        self.text = text
        self.function_calls = function_calls or []
        self.candidates = candidates or []


def get_active_model_config() -> tuple[str, str]:
    """Return the active provider and model name from environment settings."""
    provider = os.getenv('LLM_PROVIDER', 'gemini').strip().lower()
    if provider == 'openrouter':
        api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError('OPENROUTER_API_KEY is not set. Add it to the .env file at the repo root.')
        model = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free').strip()
        return 'openrouter', model

    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not set. Add it to the .env file at the repo root.')
    model = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite').strip()
    return 'gemini', model


PROVIDER, MODEL = get_active_model_config()

# Create the Gemini client if a Gemini key is available.
client = None
if PROVIDER == 'gemini':
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', '').strip())

# State used to avoid repeatedly hitting Gemini when its quota is exhausted.
# `_gemini_backoff_until` is a timestamp; while now < that timestamp we skip
# Gemini and use OpenRouter directly. `_gemini_failure_count` tracks
# consecutive quota/rate-limit failures.
_gemini_backoff_until = 0.0
_gemini_failure_count = 0


def _call_gemini_api(contents: list, model: str, system_prompt: str, tools: list):
    if client is None:
        raise RuntimeError('Gemini client is not configured.')
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=tools,
            system_instruction=system_prompt,
        )
    )


def _call_openrouter_api(contents: list, model: str, system_prompt: str, tools: list):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('openai package is required for OpenRouter fallback.') from exc

    openrouter_client = OpenAI(
        api_key=os.getenv('OPENROUTER_API_KEY', '').strip(),
        base_url='https://openrouter.ai/api/v1',
    )

    messages = []
    for content in contents:
        role = 'user' if content.role == 'user' else 'assistant'
        text_parts = []
        for part in content.parts:
            if getattr(part, 'text', None):
                text_parts.append(part.text)
        if text_parts:
            messages.append({'role': role, 'content': '\n'.join(text_parts)})

    if system_prompt:
        messages.insert(0, {'role': 'system', 'content': system_prompt})

    response = openrouter_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )

    text = ''
    if getattr(response, 'choices', None):
        text = response.choices[0].message.content or ''

    return NormalizedResponse(text=text, function_calls=[], candidates=[])

# ── Tool definitions ─────────────────────────────────────────────────
# Gemini uses FunctionDeclaration objects inside a Tool.
# The structure is similar to OpenAI but uses google.genai.types.

read_file_fn = types.FunctionDeclaration(
    name='read_file',
    description=(
        'Read the full contents of a source code file in the repository. '
        'Use this when you need to inspect a specific file to understand '
        'the code or find the root cause of a bug.'
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            'filepath': types.Schema(
                type=types.Type.STRING,
                description='Path relative to the repo root. Example: src/auth.py'
            )
        },
        required=['filepath']
    )
)

search_code_fn = types.FunctionDeclaration(
    name='search_code',
    description=(
        'Search for a keyword across all Python files in the repository. '
        'Use this first to find which files are relevant to the bug '
        'before reading any full file.'
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            'query': types.Schema(
                type=types.Type.STRING,
                description='The keyword to search for, e.g. password or KeyError'
            )
        },
        required=['query']
    )
)

edit_file_fn = types.FunctionDeclaration(
    name='edit_file',
    description=(
        'Write new content to a file in the repository. '
        'Use this to write a failing test before the fix, '
        'and then to write the fix itself.'
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            'filepath': types.Schema(
                type=types.Type.STRING,
                description='Path relative to the repo root'
            ),
            'new_content': types.Schema(
                type=types.Type.STRING,
                description='The complete file content to write'
            )
        },
        required=['filepath', 'new_content']
    )
)

run_tests_fn = types.FunctionDeclaration(
    name='run_tests',
    description=(
        'Run pytest in the repository. Returns pass/fail and output. '
        'Run this after writing the failing test to confirm it fails, '
        'and again after the fix to confirm it passes.'
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            'test_file': types.Schema(
                type=types.Type.STRING,
                description='Optional: path to a specific test file'
            )
        }
    )
)

# Bundle all four functions into one Tool object
ROVER_TOOLS = types.Tool(
    function_declarations=[
        read_file_fn,
        search_code_fn,
        edit_file_fn,
        run_tests_fn,
    ]
)

# ── System prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = '''You are Rover, an autonomous debugging agent.
Your job is to investigate a bug report and fix the bug in the codebase.

Follow this exact process:
1. Search for files related to the bug keywords (use search_code).
2. Read the relevant files (use read_file).
3. Form a hypothesis about the root cause.
4. Rate your confidence from 0 to 100. If below 50, output a
   clarifying question and stop.
5. Write a pytest test that reproduces the bug (use edit_file).
   This test should FAIL right now because the bug still exists.
6. Run the tests to confirm the test fails (use run_tests).
7. Edit the source file to apply a minimal fix (use edit_file).
8. Run the tests again to confirm the fix works (use run_tests).
9. If tests still fail, revise your hypothesis and try again.
   Maximum 3 fix attempts.

Rules:
- Only change what is needed to fix the bug. Do not refactor.
- Always write the test BEFORE the fix.
- End with a plain English summary of what you found and changed.
'''

# ── API call ─────────────────────────────────────────────────────────

def call_gemini(contents: list) -> object:
    '''
    Send the current conversation to the configured model, with automatic fallback
    to OpenRouter when Gemini hits a quota or rate-limit error.

    Args:
        contents: list of types.Content objects (the conversation history)

    Returns:
        A normalized response object that exposes text/function_calls/candidates.
    '''
    global _gemini_backoff_until, _gemini_failure_count

    provider, model = get_active_model_config()

    # If we're currently in a Gemini backoff window, skip directly to OpenRouter.
    if provider == 'gemini' and time.time() < _gemini_backoff_until:
        if os.getenv('OPENROUTER_API_KEY', '').strip() and os.getenv('OPENROUTER_MODEL', '').strip():
            logger.info('Gemini is in backoff; using OpenRouter fallback.')
            return _call_openrouter_api(contents, os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free'), SYSTEM_PROMPT, [ROVER_TOOLS])

    try:
        if provider == 'openrouter':
            return _call_openrouter_api(contents, model, SYSTEM_PROMPT, [ROVER_TOOLS])
        return _call_gemini_api(contents, model, SYSTEM_PROMPT, [ROVER_TOOLS])
    except Exception as exc:
        # If configured provider was OpenRouter, surface the error.
        if provider == 'openrouter':
            raise

        msg = str(exc)

        # Detect quota / rate-limit errors and extract retry delay if present.
        if 'RESOURCE_EXHAUSTED' in msg or '429' in msg or 'quota' in msg.lower():
            _gemini_failure_count += 1

            m = re.search(r"(\d+(?:\.\d+)?)s", msg)
            delay = float(m.group(1)) if m else None
            if delay:
                _gemini_backoff_until = time.time() + delay + 1.0
                logger.warning('Gemini quota hit; backing off for %.1fs.', delay)
            else:
                _gemini_backoff_until = time.time() + 30.0
                logger.warning('Gemini quota hit; backing off for 30s (no retry info).')

            # Immediately use OpenRouter if configured.
            if os.getenv('OPENROUTER_API_KEY', '').strip() and os.getenv('OPENROUTER_MODEL', '').strip():
                logger.info('Gemini failed (%s); falling back to OpenRouter.', exc)
                return _call_openrouter_api(contents, os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free'), SYSTEM_PROMPT, [ROVER_TOOLS])

        # Otherwise, re-raise the original exception.
        raise


# ── Structured LLM Analysis ──────────────────────────────────────────

from pydantic import BaseModel, Field

class LLMBugFinding(BaseModel):
    title: str = Field(description="Short descriptive title of the bug")
    description: str = Field(description="Detailed explanation of the issue")
    severity: str = Field(description="Severity: low, medium, high, critical")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    category: str = Field(description="Category: Security, Logic, Performance, Reliability, Code Smell, Maintainability")
    filepath: str = Field(description="Relative path to the file containing the bug")
    line_number: int = Field(description="Line number where the bug is located")
    code_snippet: str = Field(description="Code snippet containing the bug")
    reasoning: str = Field(description="Reasoning explaining why this code is a bug")
    suggested_fix: str = Field(description="Suggested code fix for the bug")
    impact: str = Field(description="Impact of the bug: low, medium, high, critical")

class LLMBugAnalysisResponse(BaseModel):
    findings: list[LLMBugFinding]


def call_llm_structured(prompt: str, response_schema) -> str:
    """
    Send a prompt expecting a structured JSON response.
    Supports fallback to OpenRouter when Gemini hits quota or rate limits.
    """
    global _gemini_backoff_until, _gemini_failure_count
    provider, model = get_active_model_config()

    use_openrouter = (provider == 'openrouter' or time.time() < _gemini_backoff_until)
    
    if use_openrouter:
        api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
        openrouter_model = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free').strip()
        if api_key:
            try:
                from openai import OpenAI
                openrouter_client = OpenAI(api_key=api_key, base_url='https://openrouter.ai/api/v1')
                messages = [
                    {"role": "system", "content": "You are a code analysis helper. You must output raw JSON matching the requested schema. No markdown wrapping, no explanation, only valid JSON."},
                    {"role": "user", "content": prompt}
                ]
                response = openrouter_client.chat.completions.create(
                    model=openrouter_model,
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.error("OpenRouter structured call failed: %s", e)
        if provider == 'openrouter':
            raise RuntimeError("OpenRouter failed.")

    try:
        if client is None:
            raise RuntimeError('Gemini client is not configured.')
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                system_instruction="You are a code analysis helper. You must output raw JSON matching the requested schema."
            )
        )
        return response.text or ""
    except Exception as exc:
        msg = str(exc)
        if 'RESOURCE_EXHAUSTED' in msg or '429' in msg or 'quota' in msg.lower():
            _gemini_failure_count += 1
            m = re.search(r"(\d+(?:\.\d+)?)s", msg)
            delay = float(m.group(1)) if m else None
            _gemini_backoff_until = time.time() + (delay or 30.0) + 1.0
            logger.warning('Gemini quota hit; backing off.')
            
            # Retry immediately with OpenRouter if available
            api_key = os.getenv('OPENROUTER_API_KEY', '').strip()
            openrouter_model = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free').strip()
            if api_key:
                try:
                    from openai import OpenAI
                    openrouter_client = OpenAI(api_key=api_key, base_url='https://openrouter.ai/api/v1')
                    messages = [
                        {"role": "system", "content": "You are a code analysis helper. You must output raw JSON matching the requested schema. No markdown wrapping, no explanation, only valid JSON."},
                        {"role": "user", "content": prompt}
                    ]
                    response = openrouter_client.chat.completions.create(
                        model=openrouter_model,
                        messages=messages,
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                    return response.choices[0].message.content or ""
                except Exception as e:
                    logger.error("OpenRouter fallback structured call failed: %s", e)
        raise