"""
agent.py

The reasoning loop that drives Rover.
Calls Gemini 2.5 Flash repeatedly, executing whatever tool functions
it requests, until the model produces a final text answer.
"""
import json
import time
from google.genai import types
from src.llm import call_gemini, SYSTEM_PROMPT
from src.tools import read_file, search_code, edit_file, run_tests

# Map tool names to the actual Python functions
TOOL_MAP = {
    'read_file':   read_file,
    'search_code': search_code,
    'edit_file':   edit_file,
    'run_tests':   run_tests,
}


def run_agent(bug_report: str) -> str:
    '''
    Run the Rover agent on a bug report.

    Args:
        bug_report: the full text of the bug description

    Returns:
        The agent's final summary as a plain text string.
    '''
    # Gemini uses types.Content objects instead of role/content dicts.
    # We start with just the user's bug report.
    # The system_instruction is passed separately in call_gemini().
    contents = [
        types.Content(
            role='user',
            parts=[types.Part.from_text(text=f"Bug report:\n\n{bug_report}")]
        )
    ]

    max_iterations = 20
    final_summary  = 'Agent completed without producing a summary.'

    for i in range(max_iterations):
        print(f'\n--- Iteration {i + 1} ---')

        response = call_gemini(contents)

        # CASE 1: no function calls means Gemini is done
        if not response.function_calls:
            final_summary = response.text or final_summary
            print('Agent finished.')
            break

        # CASE 2: Gemini wants to call one or more functions.
        # First add Gemini's response to the conversation history.
        contents.append(
            types.Content(
                role='model',
                parts=response.candidates[0].content.parts
            )
        )

        # Execute each requested function call and collect results
        tool_response_parts = []

        for fn_call in response.function_calls:
            name = fn_call.name
            args = dict(fn_call.args)   # Gemini args are already a dict

            print(f'  Calling: {name}({args})')

            # Run the actual Python function
            fn     = TOOL_MAP.get(name)
            result = fn(**args) if fn else f'ERROR: unknown tool {name}'

            preview = str(result)[:120]
            print(f'  Result:  {preview}...' if len(str(result)) > 120 else f'  Result:  {result}')

            # Build the function response part
            # Gemini expects the result as a dict with a 'result' key
            tool_response_parts.append(
                types.Part.from_function_response(
                    name=name,
                    response={'result': result}
                )
            )

        # Add all tool results as a single user turn
        contents.append(
            types.Content(
                role='user',
                parts=tool_response_parts
            )
        )

        # Loop again — Gemini will read the tool results
        # and decide what to do next

    return final_summary

from src.github_client import get_issue_text, post_comment, clone_repo, RepositoryContext
from src.github_auth import load_installation_id
from src.utils import log_run

def run_agent_for_issue(repo_name: str, issue_number: int):
    '''Full agent run triggered by a real GitHub Issue.'''
    start = time.time()
    inst_id = load_installation_id()
    ctx = RepositoryContext.from_repo_name(repo_name, inst_id)
    
    clone_repo(ctx)
    bug_report = get_issue_text(ctx, issue_number)
    print(f'Running agent on Issue #{issue_number}...')
    summary    = run_agent(bug_report)
    comment    = f'## Rover Report\n\n{summary}'
    post_comment(ctx, issue_number, comment)
    log_run(repo_name, issue_number, summary, round(time.time()-start, 1))