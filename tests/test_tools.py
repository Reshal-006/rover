"""
test_tools.py

Unit tests for the Rover tool layer.
Run with: pytest tests/test_tools.py -v
"""
import os, sys

# Make sure Python can find the src module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools import read_file, search_code, edit_file, run_tests


def test_read_file_returns_string():
    """read_file should return a non-empty string for a file that exists."""
    result = read_file('src/auth.py')
    assert isinstance(result, str)
    assert len(result) > 0


def test_read_file_handles_missing_file():
    """read_file should return an error message, not crash."""
    result = read_file('definitely/does/not/exist.py')
    assert 'ERROR' in result


def test_search_code_returns_list():
    """search_code should return a list (possibly empty)."""
    result = search_code('password')
    assert isinstance(result, list)


def test_search_code_finds_known_keyword():
    """search_code should find 'password' in the auth.py file."""
    result = search_code('password')
    # We know auth.py has the word 'password' in it
    assert len(result) > 0
    # Each result should have these three keys
    assert 'file' in result[0]
    assert 'line' in result[0]
    assert 'content' in result[0]


def test_edit_file_creates_file():
    """edit_file should create the file and return a confirmation."""
    msg = edit_file('tests/test_temp_rover.py', 'def test_x(): pass\n')
    assert 'OK' in msg
    assert os.path.exists('workspace/tests/test_temp_rover.py')


def test_run_tests_returns_correct_structure():
    """run_tests should return a dict with passed, output, errors keys."""
    result = run_tests()
    assert isinstance(result, dict)
    assert 'passed' in result
    assert 'output' in result
    assert 'errors' in result
    assert isinstance(result['passed'], bool)