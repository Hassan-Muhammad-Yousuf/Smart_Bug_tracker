import os
import subprocess
import tempfile
import uuid
import shutil

class GitIntegration:
    def __init__(self):
        self.repos_dir = os.path.join(tempfile.gettempdir(), 'bug_tracker_repos')
        os.makedirs(self.repos_dir, exist_ok=True)
    
    def clone_repository(self, repo_url):
        """
        Clone a Git repository and return the path to the cloned repo
        """
        # Create a unique directory name for this repo
        repo_dir = os.path.join(self.repos_dir, str(uuid.uuid4()))
        
        try:
            # Clone the repository
            subprocess.check_output(
                ['git', 'clone', repo_url, repo_dir],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            return repo_dir
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e.output}")
            # Clean up if the clone failed
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            return None
        except FileNotFoundError:
            print("Git command not found. Please install Git.")
            return None
    
    def get_commit_history(self, repo_path, file_path=None):
        """
        Get the commit history for a repository or specific file
        """
        try:
            if file_path:
                # Get commit history for a specific file
                output = subprocess.check_output(
                    ['git', 'log', '--pretty=format:%H|%an|%ad|%s', '--date=iso', file_path],
                    cwd=repo_path,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
            else:
                # Get commit history for the entire repository
                output = subprocess.check_output(
                    ['git', 'log', '--pretty=format:%H|%an|%ad|%s', '--date=iso'],
                    cwd=repo_path,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
            
            # Parse the output
            commits = []
            for line in output.splitlines():
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commit_hash, author, date, message = parts
                    commits.append({
                        'hash': commit_hash,
                        'author': author,
                        'date': date,
                        'message': message
                    })
            
            return commits
        except subprocess.CalledProcessError as e:
            print(f"Error getting commit history: {e.output}")
            return []
        except FileNotFoundError:
            print("Git command not found. Please install Git.")
            return []
    
    def get_file_blame(self, repo_path, file_path):
        """
        Get blame information for a file
        """
        try:
            # Get blame information
            output = subprocess.check_output(
                ['git', 'blame', '--line-porcelain', file_path],
                cwd=repo_path,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Parse the output
            blame_info = []
            current_commit = None
            
            for line in output.splitlines():
                if line.startswith('author '):
                    author = line[7:]
                elif line.startswith('author-time '):
                    author_time = line[12:]
                elif line.startswith('\t'):
                    # This is the actual line content
                    if current_commit:
                        blame_info.append({
                            'commit': current_commit,
                            'author': author,
                            'time': author_time,
                            'content': line[1:]
                        })
                elif ' ' in line:
                    # This is a new commit line
                    parts = line.split(' ', 1)
                    current_commit = parts[0]
            
            return blame_info
        except subprocess.CalledProcessError as e:
            print(f"Error getting file blame: {e.output}")
            return []
        except FileNotFoundError:
            print("Git command not found. Please install Git.")
            return []

