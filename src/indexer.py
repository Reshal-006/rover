import os
import ast
import json
import logging
from pathlib import Path

logger = logging.getLogger("rover.indexer")

# Ignored directories for indexing
IGNORED_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache", "workspace", "scans", "logs"}
SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".yaml", ".yml", ".json", ".md", ".txt"}

class RepositoryIndexer:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.index_file = self.repo_path / ".rover_index.json"

    def get_index(self) -> dict:
        """Loads index from cache if valid, otherwise builds and saves it."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    cached_index = json.load(f)
                
                # Verify mtimes of files in cache
                cache_valid = True
                for filepath, file_data in cached_index.items():
                    full_path = self.repo_path / filepath
                    if not full_path.exists() or full_path.stat().st_mtime != file_data.get("mtime"):
                        cache_valid = False
                        break
                
                if cache_valid:
                    logger.info("Loaded repository index from cache: %s", self.index_file)
                    return cached_index
            except Exception as e:
                logger.warning("Failed to load cached index: %s. Re-indexing...", e)

        # Build index
        logger.info("Building repository index for %s...", self.repo_path)
        index = self.build_index()
        self.save_index(index)
        return index

    def build_index(self) -> dict:
        index = {}
        for root, dirs, files in os.walk(self.repo_path):
            # Ignore specified directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            
            for filename in files:
                filepath = Path(root) / filename
                if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                
                rel_path = str(filepath.relative_to(self.repo_path))
                
                try:
                    mtime = filepath.stat().st_mtime
                    size = filepath.stat().st_size
                    
                    if filepath.suffix.lower() == ".py":
                        symbols = self.extract_python_symbols(filepath)
                    else:
                        symbols = self.extract_generic_symbols(filepath)
                        
                    index[rel_path] = {
                        "mtime": mtime,
                        "size": size,
                        "symbols": symbols,
                        "type": filepath.suffix.lower()
                    }
                except Exception as e:
                    logger.warning("Failed to index file %s: %s", rel_path, e)
                    
        total_symbols = 0
        for rel_path, data in index.items():
            symbols = data.get("symbols", {})
            total_symbols += len(symbols.get("classes", [])) + len(symbols.get("functions", [])) + len(symbols.get("constants", []))
        logger.info("Repository indexed: %d files indexed, %d symbols extracted.", len(index), total_symbols)
        return index

    def save_index(self, index: dict):
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
            logger.info("Saved repository index to %s", self.index_file)
        except Exception as e:
            logger.error("Failed to save repository index cache: %s", e)

    def extract_python_symbols(self, filepath: Path) -> dict:
        """Extract classes, functions, docstrings, and imports from a Python file using AST."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(filepath))
            
            classes = []
            functions = []
            imports = []
            constants = []
            
            # Module-level docstring
            module_doc = ast.get_docstring(tree) or ""
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_methods = [
                        n.name for n in node.body 
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ]
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": class_methods,
                        "docstring": ast.get_docstring(node) or ""
                    })
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only collect top-level or method functions, checking if it's nested
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node) or ""
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            constants.append(target.id)
                            
            return {
                "docstring": module_doc,
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "constants": constants
            }
        except Exception as e:
            logger.debug("AST parsing failed for %s: %s", filepath, e)
            return self.extract_generic_symbols(filepath)

    def extract_generic_symbols(self, filepath: Path) -> dict:
        """Extract keywords and basic function-like lines from non-Python files."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            lines = content.splitlines()
            functions = []
            classes = []
            
            # Look for basic function/class definitions in JS/TS/Go
            for idx, line in enumerate(lines, start=1):
                line_strip = line.strip()
                if line_strip.startswith("function ") or "=>" in line_strip:
                    functions.append({"name": line_strip, "line": idx})
                elif line_strip.startswith("class "):
                    classes.append({"name": line_strip, "line": idx})
                    
            return {
                "docstring": content[:300] + ("..." if len(content) > 300 else ""),
                "classes": classes,
                "functions": functions,
                "imports": [],
                "constants": []
            }
        except Exception:
            return {"docstring": "", "classes": [], "functions": [], "imports": [], "constants": []}
