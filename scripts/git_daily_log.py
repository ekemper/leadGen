#!/usr/bin/env python3
"""
git_daily_log.py

Generates a daily git commit log (with diffs) for a given date, saves it to logs/git_log_YYYY-MM-DD.txt,
and appends an AI-generated summary using OpenAI (optional).

Usage:
    python scripts/git_daily_log.py [--date YYYY-MM-DD] [--no-ai]

Options:
    --date YYYY-MM-DD   Specify the date for the log (defaults to today)
    --no-ai             Skip OpenAI summary generation

Requirements:
    - Must be run inside a git repository
    - OPENAI_API_KEY environment variable must be set (unless --no-ai is used)
    - openai Python package must be installed (unless --no-ai is used)

"""
import subprocess
from datetime import datetime
import os
import sys
import math
import re

def get_commit_hashes(date_str):
    """Get all commit hashes for the specified date."""
    git_command = [
        'git', 'log',
        f'--since={date_str} 00:00:00',
        f'--until={date_str} 23:59:59',
        '--pretty=format:%H'
    ]
    try:
        result = subprocess.run(git_command, capture_output=True, text=True, check=True)
        hashes = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return hashes
    except Exception as e:
        print(f"Error getting commit hashes: {e}")
        return []

def get_commit_metadata(commit_hash):
    """Get the commit hash, author, date, and message for a single commit."""
    git_command = [
        'git', 'show', commit_hash, '--no-patch', '--pretty=format:%h|%an|%ad|%s', '--date=format:%Y-%m-%d %H:%M:%S'
    ]
    try:
        result = subprocess.run(git_command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting metadata for commit {commit_hash}: {e}")
        return None

def get_commit_diff(commit_hash):
    """Get the diff for a single commit."""
    git_command = [
        'git', 'show', commit_hash, '--pretty=format:', '--unified=3'
    ]
    try:
        result = subprocess.run(git_command, capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as e:
        print(f"Error getting diff for commit {commit_hash}: {e}")
        return None

def summarize_batch(batch_diffs):
    """Summarize a batch of commit diffs using OpenAI."""
    try:
        import openai
    except ImportError:
        print("Error: openai package not installed. Install with 'pip install openai'.")
        return None
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return None
    client = openai.OpenAI(api_key=api_key)
    try:
        prompt = (
            "You are a technical writer. Summarize the following git changes (up to 3 commits), "
            "grouping and explaining them by their business/user impact, new features, bug fixes, or technical improvements. "
            "Do not organize by commit. Avoid duplication. Make the summary concise, clear, and meaningful for both non-technical stakeholders and engineers. "
            "Highlight the most important updates and explain their purpose or impact."
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Summarize these git changes for a daily changelog:\n{batch_diffs}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating batch AI summary: {e}")
        return None

def generate_final_impact_summary_from_batches(batch_summaries):
    """Generate a single, organized summary from batch summaries using OpenAI."""
    try:
        import openai
    except ImportError:
        print("Error: openai package not installed. Install with 'pip install openai'.")
        return None
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return None
    client = openai.OpenAI(api_key=api_key)
    try:
        prompt = (
            "You are a technical writer. Summarize the following batch summaries of git changes for the day, "
            "grouping and explaining them by their business/user impact, new features, bug fixes, or technical improvements. "
            "Do not organize by commit. Avoid duplication. Make the summary concise, clear, and meaningful for both non-technical stakeholders and engineers. "
            "Highlight the most important updates and explain their purpose or impact."
        )
        joined_batches = '\n'.join(batch_summaries)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Summarize these batch summaries for a daily changelog:\n{joined_batches}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating final AI summary: {e}")
        return None

def split_diff_by_file(diff):
    """Split a git diff into a list of (filename, diff) tuples."""
    file_diffs = []
    current_file = None
    current_diff = []
    for line in diff.splitlines(keepends=True):
        if line.startswith('diff --git'):
            if current_file and current_diff:
                file_diffs.append((current_file, ''.join(current_diff)))
            # Extract filename from the diff header
            match = re.search(r'diff --git a/(.*?) b/', line)
            current_file = match.group(1) if match else 'unknown'
            current_diff = [line]
        else:
            current_diff.append(line)
    if current_file and current_diff:
        file_diffs.append((current_file, ''.join(current_diff)))
    return file_diffs

def summarize_file_diff(filename, file_diff):
    try:
        import openai
    except ImportError:
        print("Error: openai package not installed. Install with 'pip install openai'.")
        return None
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return None
    client = openai.OpenAI(api_key=api_key)
    try:
        prompt = (
            f"You are a technical writer. Summarize the following git diff for the file '{filename}'. "
            "Explain the business/user impact, new features, bug fixes, or technical improvements. "
            "Make the summary concise, clear, and meaningful for both non-technical stakeholders and engineers. "
            "Highlight the most important updates and explain their purpose or impact."
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": file_diff}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating file AI summary for {filename}: {e}")
        return None

def summarize_commit_from_file_summaries(commit_meta, file_summaries):
    try:
        import openai
    except ImportError:
        print("Error: openai package not installed. Install with 'pip install openai'.")
        return None
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return None
    client = openai.OpenAI(api_key=api_key)
    try:
        prompt = (
            f"You are a technical writer. Here are summaries of changes for each file in a commit. "
            f"Commit metadata: {commit_meta}\n"
            "Summarize the overall impact of this commit, grouping and explaining by business/user impact, new features, bug fixes, or technical improvements. "
            "Make the summary concise, clear, and meaningful for both non-technical stakeholders and engineers. "
            "Highlight the most important updates and explain their purpose or impact."
        )
        joined_file_summaries = '\n'.join(file_summaries)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": joined_file_summaries}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating commit AI summary: {e}")
        return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate git commit summaries for a specific date')
    parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format (defaults to today)',
                        default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--no-ai', action='store_true', help='Skip OpenAI summary generation')
    args = parser.parse_args()

    os.makedirs('logs', exist_ok=True)
    log_file = f'logs/git_log_{args.date}.txt'

    # Get GitHub repo URL for commit links
    github_repo_url = os.environ.get('GITHUB_REPO_URL')
    if not github_repo_url:
        print("WARNING: GITHUB_REPO_URL environment variable not set. Commit links will be omitted.")

    # Write header
    with open(log_file, 'w') as f:
        f.write(f"Git Commit Log for {args.date}\n")
        f.write("=" * 80 + "\n\n")

    commit_hashes = get_commit_hashes(args.date)
    if not commit_hashes:
        print("No commits found for the specified date.")
        sys.exit(0)

    all_diffs = []
    commit_metas = []
    for commit_hash in commit_hashes:
        meta = get_commit_metadata(commit_hash)
        diff = get_commit_diff(commit_hash)
        if not meta or not diff:
            continue
        # Parse metadata
        parts = meta.split('|')
        if len(parts) >= 4:
            short_hash, author, date, message = parts[:4]
        else:
            short_hash, author, date, message = commit_hash, 'Unknown', '', ''
        # Write commit info
        with open(log_file, 'a') as f:
            f.write(f"Commit: {short_hash}\nAuthor: {author}\nDate: {date}\nMessage: {message}\n")
            if github_repo_url:
                f.write(f"GitHub Link: {github_repo_url}/commit/{commit_hash}\n")
            f.write("-" * 80 + "\n")
        all_diffs.append(f"Commit: {short_hash}\n{diff}\n")
        commit_metas.append(meta)

    if not args.no_ai and all_diffs:
        commit_summaries = []
        for idx, (meta, diff) in enumerate(zip(commit_metas, all_diffs)):
            file_diffs = split_diff_by_file(diff)
            file_summaries = []
            for filename, file_diff in file_diffs:
                file_summary = summarize_file_diff(filename, file_diff)
                if file_summary:
                    file_summaries.append(f"{filename}: {file_summary}")
                else:
                    file_summaries.append(f"{filename}: [File summary could not be generated]")
            commit_summary = summarize_commit_from_file_summaries(meta, file_summaries)
            if commit_summary:
                commit_summaries.append(commit_summary)
            else:
                commit_summaries.append("[Commit summary could not be generated]")
        final_summary = generate_final_impact_summary_from_batches(commit_summaries)
        with open(log_file, 'a') as f:
            f.write("\nFinal Daily AI Summary\n")
            f.write("=" * 80 + "\n\n")
            if final_summary:
                f.write(final_summary + "\n")
                print("Final daily AI summary appended to log file.")
            else:
                f.write("Final AI summary could not be generated.\n")
                print("Final AI summary could not be generated.")

    print(f"Successfully created git log at: {log_file}")

if __name__ == "__main__":
    main()