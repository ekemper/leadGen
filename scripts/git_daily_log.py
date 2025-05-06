#!/usr/bin/env python3

import subprocess
from datetime import datetime
import os

def get_todays_commits():
    # Get today's date in the format git expects
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Generate the log file name with today's date
    log_file = f'logs/git_log_{today}.txt'
    
    # Git command to get all commits from today with full details
    git_command = [
        'git', 'log',
        '--since="00:00:00"',
        '--until="23:59:59"',
        '--pretty=format:"%h|%an|%ad|%s|%b"',
        '--date=format:"%Y-%m-%d %H:%M:%S"',
        '--stat'
    ]
    
    try:
        # Run the git command and capture output
        result = subprocess.run(git_command, capture_output=True, text=True, check=True)
        
        # Write the output to the log file
        with open(log_file, 'w') as f:
            f.write(f"Git Commit Log for {today}\n")
            f.write("=" * 80 + "\n\n")
            f.write(result.stdout)
        
        print(f"Successfully created git log at: {log_file}")
        return log_file
        
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}")
        return None
    except Exception as e:
        print(f"Error writing log file: {e}")
        return None

if __name__ == "__main__":
    get_todays_commits() 