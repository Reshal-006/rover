import os
import sys
import tempfile
import json
from pathlib import Path

# Add src to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indexer import RepositoryIndexer

def test_indexer_builds_and_caches():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create a mock python file
        py_file = tmp_path / "mock_module.py"
        py_file.write_text("""
\"\"\"This is a module docstring.\"\"\"
GLOBAL_CONSTANT = "hello"

class MockClass:
    \"\"\"This is a class docstring.\"\"\"
    def method_one(self):
        pass

def top_level_function(arg1):
    \"\"\"Function docstring.\"\"\"
    return arg1
""", encoding="utf-8")

        # Create a mock js file
        js_file = tmp_path / "mock_script.js"
        js_file.write_text("""
function jsFunction() {
    return 42;
}
""", encoding="utf-8")

        indexer = RepositoryIndexer(tmpdir)
        index = indexer.get_index()
        
        # Verify index structure
        assert "mock_module.py" in index
        assert "mock_script.js" in index
        
        # Verify Python symbol parsing
        py_data = index["mock_module.py"]
        assert py_data["type"] == ".py"
        symbols = py_data["symbols"]
        assert symbols["docstring"] == "This is a module docstring."
        assert any(c["name"] == "MockClass" for c in symbols["classes"])
        assert any(f["name"] == "top_level_function" for f in symbols["functions"])
        assert "GLOBAL_CONSTANT" in symbols["constants"]
        
        # Verify JS symbol parsing
        js_data = index["mock_script.js"]
        assert js_data["type"] == ".js"
        assert any("jsFunction" in f["name"] for f in js_data["symbols"]["functions"])
        
        # Verify cache file created
        assert (tmp_path / ".rover_index.json").exists()
        
        # Verify cache mtime loader
        index_cached = indexer.get_index()
        assert index_cached == index
