"""
tools.py

The four functions Rover uses to interact with the codebase.
These are called by the GPT-4o agent during the reasoning loop.
"""
import os
import subprocess
import sys

# All file operations happen inside this folder
WORKSPACE = 'workspace'


def read_file(filepath: str, workspace_dir: str = WORKSPACE) -> str:
    """
    Read the contents of a file from the cloned workspace repo.

    Args:
        filepath: path relative to the repo root, e.g. 'src/auth.py'
        workspace_dir: target workspace folder, defaults to 'workspace'

    Returns:
        The file contents as a string, or an error message.
    """
    full_path = os.path.join(workspace_dir, filepath)

    if not os.path.exists(full_path):
        return f'ERROR: File not found: {filepath}'

    with open(full_path, 'r', errors='ignore') as f:
        content = f.read()

    # Safety limit: cap at 8000 chars to avoid overloading the model
    if len(content) > 8000:
        return content[:8000] + '\n... [file truncated at 8000 chars]'

    return content


def search_code(query: str, file_extension: str = '.py', workspace_dir: str = WORKSPACE) -> list:
    """
    Search for a keyword across all files in the workspace.

    Args:
        query: the keyword to search for, e.g. 'password' or 'KeyError'
        file_extension: which file types to search, default .py
        workspace_dir: target workspace folder, defaults to 'workspace'

    Returns:
        List of dicts with 'file', 'line' (number), 'content' (the line).
        Capped at 20 results.
    """
    matches = []

    for root, dirs, files in os.walk(workspace_dir):
        # Skip folders that are not source code
        dirs[:] = [d for d in dirs
                   if d not in ['.git', '__pycache__', '.venv', 'node_modules']]

        for filename in files:
            if filename.endswith(file_extension):
                filepath = os.path.join(root, filename)

                with open(filepath, 'r', errors='ignore') as f:
                    for line_num, line in enumerate(f, start=1):
                        if query.lower() in line.lower():
                            rel_file = os.path.relpath(filepath, workspace_dir)
                            matches.append({
                                'file': rel_file,
                                'line': line_num,
                                'content': line.strip()
                            })

    return matches[:20]  # cap at 20 to keep the model prompt manageable


def edit_file(filepath: str, new_content: str, workspace_dir: str = WORKSPACE) -> str:
    """
    Write new content to a file in the workspace.
    Creates the file and any missing parent folders if needed.

    Args:
        filepath: path relative to repo root, e.g. 'tests/test_auth.py'
        new_content: the complete content to write to the file
        workspace_dir: target workspace folder, defaults to 'workspace'

    Returns:
        A confirmation string.
    """
    full_path = os.path.join(workspace_dir, filepath)

    # Create parent directories if they do not exist
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, 'w') as f:
        f.write(new_content)

    return f'OK: wrote {len(new_content)} characters to {filepath}'


def run_tests(test_file: str = None, workspace_dir: str = WORKSPACE) -> dict:
    """
    Run pytest in the workspace directory.

    Args:
        test_file: optional path to a specific test file.
                   If None, runs the full test suite.
        workspace_dir: target workspace folder, defaults to 'workspace'

    Returns:
        Dict with:
            'passed' (bool): True if all tests passed
            'output' (str): the pytest terminal output
            'errors' (str): any stderr output
    """
    cmd = [sys.executable, '-m', 'pytest', '-v', '--tb=short']
    
    if test_file:
        cmd.append(test_file)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=workspace_dir   # run pytest INSIDE the cloned repo
    )

    return {
        'passed': result.returncode == 0,
        'output': result.stdout[-3000:],   # last 3000 chars
        'errors': result.stderr[-500:]
    }