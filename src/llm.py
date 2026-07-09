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

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise RuntimeError('GEMINI_API_KEY is not set. Add it to the .env file at the repo root.')

# Create the Gemini client using your API key
client = genai.Client(api_key=api_key)

MODEL = 'gemini-3.1-flash-lite'

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
    Send the current conversation to Gemini and get a response.

    Args:
        contents: list of types.Content objects (the conversation history)

    Returns:
        The full GenerateContentResponse object.
    '''
    return client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=[ROVER_TOOLS],
            system_instruction=SYSTEM_PROMPT,
        )
    )