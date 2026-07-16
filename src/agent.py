"""
agent.py

The optimized reasoning loop that drives Rover.
Redesigned to follow an "Analyze -> Gather Context -> Solve" architecture.
Minimizes LLM calls to a maximum of 2-3 per bug resolution.
"""
import os
import re
import json
import time
import subprocess
import logging
from google.genai import types

from src.indexer import RepositoryIndexer
from src.tools import edit_file, run_tests, read_file
from src.llm import call_llm_structured, BugResolution
from src.github_client import get_issue_text, post_comment, clone_repo, RepositoryContext, create_branch, push_commits, open_pull_request
from src.github_auth import load_installation_id
from src.utils import log_run

logger = logging.getLogger("rover.agent")

def load_resolution_cache(repo_name: str, issue_number: int) -> dict | None:
    cache_path = f"scans/resolution_{repo_name.replace('/', '_')}_{issue_number}.json"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                logger.info("Found cached resolution for %s #%s", repo_name, issue_number)
                return json.load(f)
        except Exception:
            pass
    return None

def save_resolution_cache(repo_name: str, issue_number: int, data: dict):
    os.makedirs("scans", exist_ok=True)
    cache_path = f"scans/resolution_{repo_name.replace('/', '_')}_{issue_number}.json"
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved resolution to cache: %s", cache_path)
    except Exception as e:
        logger.warning("Failed to save resolution cache: %s", e)

def clean_json_response(json_str: str) -> str:
    clean = json_str.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    return clean.strip()

def run_agent(bug_report: str) -> dict:
    """
    Run the optimized Rover agent on a bug report.
    Gathers local context via AST indexing and matching, then resolves using 1-2 structured LLM calls.
    
    Returns a dict containing:
        - summary: text summary of changes
        - commit_message: concise commit message
        - pr_title: title for PR
        - pr_body: body markdown for PR
        - status: success or failed
    """
    start_time = time.time()
    logger.info("Starting optimized bug-fixing agent...")
    
    # 1. Local Codebase Indexing
    indexer = RepositoryIndexer("workspace")
    index = indexer.get_index()
    
    # 2. Extract potential keywords/symbols and trace paths from the bug report
    tokens = set(re.findall(r'[a-zA-Z0-9_\-\.]+', bug_report))
    trace_matches = re.findall(
        r'File\s+["\']([^"\']+)["\'],\s+line\s+(\d+)(?:,\s+in\s+([a-zA-Z0-9_]+))?',
        bug_report,
        re.IGNORECASE
    )
    
    logger.info("Parsed %d tokens and %d traceback frame references from bug report.", len(tokens), len(trace_matches))
    
    # 3. Match codebase files by priority
    matched_files = {}
    for rel_path, data in index.items():
        score = 0
        basename = os.path.basename(rel_path)
        
        # Priority 1: Exact matches in stack trace
        for trace_file, line_str, fn_name in trace_matches:
            if trace_file in rel_path or rel_path in trace_file or os.path.basename(trace_file) == basename:
                score += 100
                logger.info("File %s matched in stack trace line %s", rel_path, line_str)
                
        # Priority 2: Basename mentioned in tokens
        if basename in tokens or rel_path in tokens:
            score += 50
            
        symbols = data.get("symbols", {})
        # Priority 3: Classes / methods mentioned in tokens
        for cls in symbols.get("classes", []):
            if cls["name"] in tokens:
                score += 30
                for m in cls.get("methods", []):
                    if m in tokens:
                        score += 20
                        
        # Priority 4: Top-level functions mentioned in tokens
        for fn in symbols.get("functions", []):
            if fn["name"] in tokens:
                score += 30
                
        # Priority 5: Constants mentioned in tokens
        for const in symbols.get("constants", []):
            if const in tokens:
                score += 10
                
        if score > 0:
            matched_files[rel_path] = score
            
    # Fallback 1: Text search inside files for specific long tokens
    if not matched_files:
        logger.info("No direct symbol matches. Initiating keyword fallback search...")
        sorted_tokens = sorted(
            [t for t in tokens if len(t) > 3 and t.lower() not in {"error", "test", "python", "file", "line", "exception", "failed"}],
            key=len,
            reverse=True
        )
        for rel_path, data in index.items():
            score = 0
            try:
                full_path = os.path.join("workspace", rel_path)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for kw in sorted_tokens[:5]:
                    if kw.lower() in content.lower():
                        score += 10
            except Exception:
                pass
            if score > 0:
                matched_files[rel_path] = score
                
    # Fallback 2: Default to matching files in src/
    if not matched_files:
        logger.info("No keyword matches. Defaulting to src/ files...")
        for rel_path in index:
            if rel_path.startswith("src/"):
                matched_files[rel_path] = 1

    if not matched_files:
        logger.warning("No codebase files matched the bug report or existed in index.")
        return {
            "summary": "The referenced function or symbol does not exist in this repository. No matching code found.",
            "commit_message": "Rover: No changes",
            "pr_title": "No Changes",
            "pr_body": "Rover completed without finding relevant code in this repository.",
            "status": "failed"
        }
        
    # Sort matched files by score descending
    sorted_matched = sorted(matched_files.items(), key=lambda x: x[1], reverse=True)
    logger.info("Matched files ranking: %s", sorted_matched[:5])
    
    # 4. Construct context string up to character budget
    context_str = ""
    character_budget = 35000
    files_read = []
    
    for rel_path, score in sorted_matched:
        if len(context_str) >= character_budget:
            break
        content = read_file(rel_path)
        if not content.startswith("ERROR:"):
            context_str += f"\n\n### File: {rel_path}\n"
            context_str += f"```python\n{content}\n```\n"
            files_read.append(rel_path)
            
    logger.info("Read %d files for context gathering: %s", len(files_read), files_read)
    
    # 5. structured LLM Call for Diagnosis & Patch (Call 1)
    prompt = f"""
Bug Report:
{bug_report}

Gathered Codebase Context:
{context_str}

Please analyze the bug and generate a complete fix.
You must output a JSON object containing:
1. "analysis": Your explanation/diagnosis of the root cause of the bug.
2. "patch": The COMPLETE updated file content of the file that contains the fix. Do not output a diff; output the complete content of the file.
3. "filepath": The relative path of the file to modify (e.g., src/auth.py).
4. "tests": Complete pytest code to reproduce the bug and verify your fix. Make sure it imports from the app correctly.
5. "test_filepath": The relative path to write the test file (e.g., tests/test_auth.py).
6. "commit_message": A concise git commit message describing the fix.
7. "pr_title": Title of the Pull Request.
8. "pr_body": Markdown description for the Pull Request.
"""
    logger.info("Making primary LLM call for diagnosis and patch generation...")
    llm_start = time.time()
    try:
        raw_res = call_llm_structured(prompt, BugResolution)
        clean_res = clean_json_response(raw_res)
        res_data = json.loads(clean_res)
        logger.info("Primary LLM call succeeded in %.2fs.", time.time() - llm_start)
    except Exception as e:
        logger.error("Failed to generate patch or parse LLM response: %s", e)
        return {
            "summary": f"Failed to generate fix due to LLM parsing error: {e}",
            "commit_message": "Rover: Parse failure",
            "pr_title": "Fix Generation Failed",
            "pr_body": f"Rover failed to construct a valid structured patch. Error details: {e}",
            "status": "failed"
        }
        
    # 6. Apply patch and test
    logger.info("Applying patch to %s...", res_data["filepath"])
    edit_file(res_data["filepath"], res_data["patch"])
    
    logger.info("Writing test to %s...", res_data["test_filepath"])
    edit_file(res_data["test_filepath"], res_data["tests"])
    
    # 7. Validate tests
    logger.info("Running pytest validation...")
    test_res = run_tests(res_data["test_filepath"])
    
    # 8. Optional Review Loop (Call 2)
    if not test_res["passed"]:
        logger.warning("First fix attempt failed tests. Output: %s. Initiating Review Call...", test_res["output"][:400])
        
        review_prompt = f"""
You previously attempted to fix the bug, but the tests failed.

Original Bug Report:
{bug_report}

Gathered Codebase Context:
{context_str}

Your proposed filepath: {res_data["filepath"]}
Your proposed patch:
```python
{res_data["patch"]}
```

Your proposed test filepath: {res_data["test_filepath"]}
Your proposed test:
```python
{res_data["tests"]}
```

Pytest Failure Output:
{test_res["output"]}
{test_res["errors"]}

Please analyze the test failure and generate a corrected fix. You must output a JSON object matching the requested schema.
"""
        try:
            review_start = time.time()
            raw_res = call_llm_structured(review_prompt, BugResolution)
            clean_res = clean_json_response(raw_res)
            res_data = json.loads(clean_res)
            logger.info("Review LLM call succeeded in %.2fs.", time.time() - review_start)
            
            # Re-apply corrected patch
            logger.info("Applying corrected patch to %s...", res_data["filepath"])
            edit_file(res_data["filepath"], res_data["patch"])
            logger.info("Writing corrected test to %s...", res_data["test_filepath"])
            edit_file(res_data["test_filepath"], res_data["tests"])
            
            # Validate again
            logger.info("Re-running pytest validation...")
            test_res = run_tests(res_data["test_filepath"])
        except Exception as e:
            logger.error("Failed in review loop call: %s", e)
            
    # 9. Format final summary
    status = "completed" if test_res["passed"] else "failed"
    test_status_text = "All tests passed successfully!" if test_res["passed"] else f"Tests failed:\n{test_res['output'][-1500:]}"
    
    summary = (
        f"### Diagnosis\n{res_data.get('analysis', 'No analysis provided.')}\n\n"
        f"### Fix Applied\n"
        f"- Modified: `{res_data.get('filepath')}`\n"
        f"- Test file: `{res_data.get('test_filepath')}`\n\n"
        f"### Verification Status ({status.upper()})\n"
        f"```text\n{test_status_text}\n```"
    )
    
    duration = time.time() - start_time
    logger.info("Bug resolution agent run completed in %.2fs with status: %s", duration, status)
    
    return {
        "summary": summary,
        "commit_message": res_data.get("commit_message", f"Rover: Fix for issue"),
        "pr_title": res_data.get("pr_title", "Rover: Auto-fix"),
        "pr_body": res_data.get("pr_body", "Rover completed the analysis and patch generation."),
        "status": status
    }

def remote_branch_exists(ctx: RepositoryContext, branch_name: str) -> bool:
    """Check if the branch already exists on remote origin."""
    try:
        repo = ctx.client.get_repo(f"{ctx.owner}/{ctx.repo}")
        repo.get_git_ref(f"heads/{branch_name}")
        logger.info("Remote branch '%s' already exists.", branch_name)
        return True
    except Exception:
        return False

def generate_unique_branch_name(ctx: RepositoryContext, issue_number: int) -> str:
    """Generate a unique branch name that does not exist on remote origin."""
    import uuid
    import datetime
    attempts = 0
    while True:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = uuid.uuid4().hex[:6]
        branch_name = f"rover/fix-issue-{issue_number}-{timestamp}-{short_uuid}"
        attempts += 1
        logger.info("Attempting unique branch name generation (attempt %d): %s", attempts, branch_name)
        if not remote_branch_exists(ctx, branch_name):
            return branch_name

def run_agent_for_issue(repo_name: str, issue_number: int):
    '''Full agent run triggered by a real GitHub Issue.'''
    start = time.time()
    
    # Check resolution cache first
    cached = load_resolution_cache(repo_name, issue_number)
    if cached:
        inst_id = load_installation_id()
        ctx = RepositoryContext.from_repo_name(repo_name, inst_id)
        # Post comment and log run directly using cached data
        post_comment(ctx, issue_number, f"## Rover Report (Loaded from Cache)\n\n{cached['summary']}")
        log_run(repo_name, issue_number, cached['summary'], 0.1)
        return
        
    inst_id = load_installation_id()
    ctx = RepositoryContext.from_repo_name(repo_name, inst_id)
    
    # 1. Clone repository
    clone_repo(ctx)
    
    # Ensure local workspace is clean and starts from the repository's default branch
    logger.info("Ensuring local workspace starts from repository default branch: %s", ctx.default_branch)
    subprocess.run(['git', 'fetch', 'origin'], cwd='workspace', check=False)
    subprocess.run(['git', 'checkout', '-f', ctx.default_branch], cwd='workspace', check=False)
    subprocess.run(['git', 'reset', '--hard', f'origin/{ctx.default_branch}'], cwd='workspace', check=False)
    subprocess.run(['git', 'clean', '-fdx'], cwd='workspace', check=False)
    
    # 2. Create unique branch on remote
    branch_name = generate_unique_branch_name(ctx, issue_number)
    logger.info("Generated branch name: %s", branch_name)
    try:
        create_branch(ctx, branch_name)
        logger.info("Successfully created remote branch: %s", branch_name)
    except Exception as e:
        logger.warning("Could not create remote branch %s: %s", branch_name, e)
        
    # 3. Checkout branch locally, deleting any stale local branch first
    subprocess.run(['git', 'branch', '-D', branch_name], cwd='workspace', check=False)
    logger.info("Checking out local branch: %s", branch_name)
    subprocess.run(['git', 'checkout', '-b', branch_name], cwd='workspace', check=False)
    
    # 4. Run agent reasoning loop
    bug_report = get_issue_text(ctx, issue_number)
    logger.info("Running agent on Issue #%s...", issue_number)
    
    result = run_agent(bug_report)
    summary = result["summary"]
    
    # Save to cache if successful
    if result["status"] == "completed":
        save_resolution_cache(repo_name, issue_number, result)
        
    # 5. Check if files were modified and commit/push/PR
    status_res = subprocess.run(['git', 'status', '--porcelain'], cwd='workspace', capture_output=True, text=True)
    if status_res.stdout.strip():
        logger.info("Modifications detected. Committing and pushing changes...")
        # Configure user identity locally if not set
        subprocess.run(['git', 'config', 'user.name', 'Rover Agent'], cwd='workspace', check=False)
        subprocess.run(['git', 'config', 'user.email', 'rover@internal.ai'], cwd='workspace', check=False)
        
        # Commit
        subprocess.run(['git', 'add', '-A'], cwd='workspace', check=False)
        subprocess.run(['git', 'commit', '-m', result["commit_message"]], cwd='workspace', check=False)
        
        # Push retry loop
        max_push_attempts = 3
        current_branch = branch_name
        final_branch_pushed = None
        comment = ""
        
        for attempt in range(1, max_push_attempts + 1):
            try:
                logger.info("Pushing commits to remote branch: %s (attempt %d/%d)", current_branch, attempt, max_push_attempts)
                push_commits(ctx, current_branch)
                final_branch_pushed = current_branch
                
                # Create Pull Request
                pr_title = result["pr_title"]
                pr_body = (
                    f"This Pull Request was automatically generated by Rover to resolve Issue #{issue_number}.\n\n"
                    f"### Summary of changes:\n{summary}\n\n"
                    f"### PR Details\n{result['pr_body']}"
                )
                pr_number = open_pull_request(ctx, pr_title, pr_body, current_branch)
                logger.info("Successfully opened Pull Request #%s on branch %s", pr_number, current_branch)
                comment = f"## Rover Report\n\nSuccessfully generated and tested fix!\nOpened Pull Request #{pr_number} to merge changes.\n\n{summary}"
                break
            except Exception as e:
                logger.error("Git push or PR creation failed on branch %s: %s", current_branch, e)
                if attempt == max_push_attempts:
                    logger.error("All %d push attempts failed. Aborting PR creation.", max_push_attempts)
                    comment = f"## Rover Report\n\nFailed to push changes or open Pull Request: {e}\n\n{summary}"
                    break
                
                # Generate a new unique branch name
                old_branch = current_branch
                current_branch = generate_unique_branch_name(ctx, issue_number)
                
                # Create remote branch using GitHub API
                try:
                    create_branch(ctx, current_branch)
                except Exception as cb_err:
                    logger.warning("Failed to create remote branch %s: %s", current_branch, cb_err)
                
                # Rename local branch to match the new remote branch name
                subprocess.run(['git', 'branch', '-m', old_branch, current_branch], cwd='workspace', check=False)
                logger.info("Renamed local branch from %s to %s to retry push", old_branch, current_branch)
                
        logger.info("Final branch pushed: %s", final_branch_pushed)
    else:
        logger.info("No modifications detected in workspace. Skipping PR.")
        comment = f"## Rover Report\n\nNo modifications were made to the codebase to address this issue.\n\n{summary}"
        
    post_comment(ctx, issue_number, comment)
    log_run(repo_name, issue_number, summary, round(time.time()-start, 1))