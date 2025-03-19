from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
import uuid
import tempfile
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import json
import re
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Import our custom modules
from analyzers.analyzer_factory import AnalyzerFactory
from models.bug_classifier import BugClassifier
from utils.git_integration import GitIntegration
from utils.code_utils import detect_language, get_file_extension
from utils.ai_integration import AICodeFixer  # Import our new AI integration

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['DATABASE'] = 'database/bug_tracker.db'
app.config['ENABLE_AI_SUGGESTIONS'] = True  # Enable AI suggestions by default

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
analyzer_factory = AnalyzerFactory()
bug_classifier = BugClassifier()
git_integration = GitIntegration()
ai_code_fixer = AICodeFixer()  # Initialize our AI code fixer

def get_db_connection():
    """Get a connection to the SQLite database with improved handling for concurrent access"""
    max_retries = 5
    retry_delay = 0.1  # seconds
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(app.config['DATABASE'], timeout=20)  # Increase timeout
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"Database is locked, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise
    
    # If we get here, all retries failed
    raise sqlite3.OperationalError("Could not connect to database after multiple attempts")

# Add Jinja2 filter for nl2br (newline to break)
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        return re.sub(r'\n', '<br>', value)
    return ''

def init_db():
    with app.app_context():
        # Check if we need to update the schema
        need_update = False
        if os.path.exists(app.config['DATABASE']):
            conn = get_db_connection()
            # Check if the bugs table has the status column
            try:
                conn.execute('SELECT status FROM bugs LIMIT 1')
            except sqlite3.OperationalError:
                need_update = True
            conn.close()
            
            if need_update:
                print("Database schema needs to be updated. Creating new database...")
                # Backup the old database
                backup_path = app.config['DATABASE'] + '.backup'
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(app.config['DATABASE'], backup_path)
        
        # Create or recreate the database
        db = get_db_connection()
        with open('database/schema.sql') as f:
            db.executescript(f.read())
        
        # Load additional fixes if the file exists
        if os.path.exists('database/fixes.sql'):
            with open('database/fixes.sql') as f:
                db.executescript(f.read())
        
        db.commit()
        db.close()
        
        if need_update:
            print("Database schema updated successfully.")

def get_current_user():
    # In a real app, this would use proper authentication
    # For now, we'll just return the default admin user
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = 1').fetchone()
    conn.close()
    return user

def log_bug_history(bug_id, user_id, field, old_value, new_value):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO bug_history (bug_id, user_id, field_changed, old_value, new_value, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (bug_id, user_id, field, old_value, new_value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def generate_ai_fix_for_bug(bug_id, code_snippet=None):
    """
    Generate an AI-powered fix suggestion for a bug and store it in the database.
    
    Args:
        bug_id (int): The ID of the bug
        code_snippet (str, optional): The code snippet containing the bug
        
    Returns:
        dict: The AI fix suggestion
    """
    conn = get_db_connection()
    bug = conn.execute('SELECT * FROM bugs WHERE id = ?', (bug_id,)).fetchone()
    
    if not bug:
        conn.close()
        return None
    
    # If no code snippet provided, try to extract it
    if not code_snippet:
        if bug['file_path'].startswith('pasted_code_'):
            # Try to get from session
            code_snippet = session.get('last_analyzed_code', '')
        else:
            # For uploaded files, extract code context from the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], bug['file_path'])
            if os.path.exists(file_path):
                code_snippet = ai_code_fixer.extract_code_context(file_path, bug['line_number'])
    
    # Generate the AI fix
    ai_fix = ai_code_fixer.generate_fix(
        code_snippet=code_snippet,
        error_message=bug['message'],
        language=bug['language'],
        line_number=bug['line_number']
    )
    
    # Store the AI fix in the database
    conn.execute(
        'INSERT INTO suggested_fixes (bug_id, language, suggestion, code_example) VALUES (?, ?, ?, ?)',
        (bug_id, bug['language'], ai_fix['suggestion'], ai_fix['code_example'])
    )
    conn.commit()
    conn.close()
    
    return ai_fix

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    # Get bug statistics
    stats = {
        'total': conn.execute('SELECT COUNT(*) FROM bugs').fetchone()[0],
        'critical': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "critical"').fetchone()[0],
        'high': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "high"').fetchone()[0],
        'medium': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "medium"').fetchone()[0],
        'low': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "low"').fetchone()[0],
        'open': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "open"').fetchone()[0],
        'in_progress': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "in_progress"').fetchone()[0],
        'fixed': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "fixed"').fetchone()[0],
        'closed': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "closed"').fetchone()[0]
    }

    # Get recent bugs
    recent_bugs = conn.execute(
        'SELECT bugs.*, users.username as assigned_to_name FROM bugs LEFT JOIN users ON bugs.assigned_to = users.id ORDER BY bugs.created_at DESC LIMIT 10'
    ).fetchall()

    # Get language distribution
    lang_dist = conn.execute(
        'SELECT language, COUNT(*) as count FROM bugs GROUP BY language'
    ).fetchall()

    # Get status distribution
    status_dist = conn.execute(
        'SELECT status, COUNT(*) as count FROM bugs GROUP BY status'
    ).fetchall()

    conn.close()

    return render_template(
        'dashboard.html', 
        stats=stats, 
        recent_bugs=recent_bugs,
        lang_dist=lang_dist,
        status_dist=status_dist
    )

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            # Create a unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Detect language
            language = detect_language(filepath)
            
            if not language:
                flash('Could not detect language of the uploaded file')
                return redirect(request.url)
            
            # Analyze the file
            analyzer = analyzer_factory.get_analyzer(language)
            if not analyzer:
                flash(f'No analyzer available for {language}')
                return redirect(request.url)
            
            analysis_results = analyzer.analyze(filepath)
            
            # Classify and prioritize bugs
            for result in analysis_results:
                result['severity'] = bug_classifier.classify(
                    language, 
                    result.get('type', ''), 
                    result.get('message', '')
                )
            
            # Store results in database
            conn = get_db_connection()
            current_time = datetime.now().isoformat()
            bug_ids = []  # Store bug IDs for AI fix generation
            
            try:
                for result in analysis_results:
                    # Ensure type is never null
                    bug_type = result.get('type', 'unknown')
                    if not bug_type:
                        bug_type = 'unknown'
                        
                    cursor = conn.execute(
                        'INSERT INTO bugs (file_path, language, line_number, column_number, message, type, severity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (
                            filename,
                            language,
                            result.get('line', 0),
                            result.get('column', 0),
                            result.get('message', ''),
                            bug_type,  # Use the validated type
                            result.get('severity', 'medium'),
                            'open',
                            current_time,
                            current_time
                        )
                    )
                    bug_ids.append(cursor.lastrowid)
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                flash(f'Error storing results: {str(e)}')
            finally:
                conn.close()
            
            # Generate AI fix suggestions for each bug if enabled
            if app.config['ENABLE_AI_SUGGESTIONS'] and bug_ids:
                for bug_id in bug_ids:
                    try:
                        # Extract code context and generate AI fix
                        code_context = ai_code_fixer.extract_code_context(filepath, result.get('line', 0))
                        generate_ai_fix_for_bug(bug_id, code_context)
                    except Exception as e:
                        print(f"Error generating AI fix for bug {bug_id}: {str(e)}")
            
            # Redirect to results page
            return redirect(url_for('analysis_results', filename=unique_filename))

    return render_template('upload.html')

@app.route('/analyze-code', methods=['GET', 'POST'])
def analyze_code():
    if request.method == 'POST':
        code = request.form.get('code')
        language = request.form.get('language')
        
        if not code:
            flash('No code provided')
            return redirect(request.url)
        
        if not language:
            flash('Please select a language')
            return redirect(request.url)
        
        # Store the code in the session for later use in AI fix generation
        session['last_analyzed_code'] = code
        
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{language}') as temp:
            temp_path = temp.name
            temp.write(code.encode('utf-8'))
        
        # Analyze the file
        analyzer = analyzer_factory.get_analyzer(language)
        if not analyzer:
            flash(f'No analyzer available for {language}')
            os.unlink(temp_path)
            return redirect(request.url)
        
        analysis_results = analyzer.analyze(temp_path)
        
        # Classify and prioritize bugs
        for result in analysis_results:
            result['severity'] = bug_classifier.classify(
                language, 
                result.get('type', ''), 
                result.get('message', '')
            )
        
        # Store results in database
        conn = get_db_connection()
        current_time = datetime.now().isoformat()
        filename = f"pasted_code_{language}"
        bug_ids = []  # Store bug IDs for AI fix generation

        try:
            for result in analysis_results:
                # Ensure type is never null
                bug_type = result.get('type', 'unknown')
                if not bug_type:
                    bug_type = 'unknown'
                    
                cursor = conn.execute(
                    'INSERT INTO bugs (file_path, language, line_number, column_number, message, type, severity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        filename,
                        language,
                        result.get('line', 0),
                        result.get('column', 0),
                        result.get('message', ''),
                        bug_type,  # Use the validated type
                        result.get('severity', 'medium'),
                        'open',
                        current_time,
                        current_time
                    )
                )
                bug_ids.append(cursor.lastrowid)
            
            conn.commit()
            
            # Get the inserted bugs
            bugs = conn.execute(
                'SELECT * FROM bugs WHERE file_path = ? ORDER BY severity, line_number',
                (filename,)
            ).fetchall()
        except Exception as e:
            conn.rollback()
            flash(f'Error storing results: {str(e)}')
            bugs = []
        finally:
            conn.close()
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
        # Generate AI fix suggestions for each bug if enabled
        if app.config['ENABLE_AI_SUGGESTIONS'] and bug_ids:
            for bug_id in bug_ids:
                try:
                    generate_ai_fix_for_bug(bug_id, code)
                except Exception as e:
                    print(f"Error generating AI fix for bug {bug_id}: {str(e)}")
        
        # Render the results
        return render_template('code_analysis_results.html', code=code, language=language, results=bugs)

    return render_template('analyze_code.html')

@app.route('/git-repo', methods=['GET', 'POST'])
def git_repo():
    if request.method == 'POST':
        repo_url = request.form.get('repo_url')
        if not repo_url:
            flash('No repository URL provided')
            return redirect(request.url)
        
        # Clone the repository
        repo_path = git_integration.clone_repository(repo_url)
        if not repo_path:
            flash('Failed to clone repository')
            return redirect(request.url)
        
        # Analyze all files in the repository
        results = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                filepath = os.path.join(root, file)
                ext = get_file_extension(filepath)
                language = None
                
                # Map file extensions to languages
                if ext in ['.py']:
                    language = 'python'
                elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                    language = 'javascript'
                elif ext in ['.java']:
                    language = 'java'
                elif ext in ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx']:
                    language = 'cpp'
                elif ext in ['.go']:
                    language = 'go'
                
                # Skip files with unknown language
                if not language:
                    continue
                
                analyzer = analyzer_factory.get_analyzer(language)
                if analyzer:
                    file_results = analyzer.analyze(filepath)
                    
                    # Classify and prioritize bugs
                    for result in file_results:
                        result['severity'] = bug_classifier.classify(
                            language, 
                            result.get('type', ''), 
                            result.get('message', '')
                        )
                        result['file_path'] = os.path.relpath(filepath, repo_path)
                        # Make sure language is set
                        result['language'] = language
                    
                    results.extend(file_results)
        
        # Store results in database
        conn = get_db_connection()
        current_time = datetime.now().isoformat()
        bug_ids = []  # Store bug IDs for AI fix generation

        try:
            for result in results:
                # Ensure type is never null
                bug_type = result.get('type', 'unknown')
                if not bug_type:
                    bug_type = 'unknown'
                
                # Ensure language is never null
                language = result.get('language')
                if not language:
                    continue  # Skip results without language
                
                cursor = conn.execute(
                    'INSERT INTO bugs (file_path, language, line_number, column_number, message, type, severity, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        result.get('file_path', ''),
                        language,
                        result.get('line', 0),
                        result.get('column', 0),
                        result.get('message', ''),
                        bug_type,  # Use the validated type
                        result.get('severity', 'medium'),
                        'open',
                        current_time,
                        current_time
                    )
                )
                bug_ids.append(cursor.lastrowid)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            flash(f'Error storing results: {str(e)}')
        finally:
            conn.close()
        
        # Generate AI fix suggestions for each bug if enabled
        if app.config['ENABLE_AI_SUGGESTIONS'] and bug_ids:
            for bug_id in bug_ids:
                try:
                    generate_ai_fix_for_bug(bug_id)
                except Exception as e:
                    print(f"Error generating AI fix for bug {bug_id}: {str(e)}")
        
        # Redirect to dashboard
        return redirect(url_for('dashboard'))

    return render_template('git_repo.html')

@app.route('/results/<filename>')
def analysis_results(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        flash('File not found')
        return redirect(url_for('index'))

    # Get results from database
    conn = get_db_connection()
    original_filename = filename.split('_', 1)[1]  # Remove UUID prefix
    results = conn.execute(
        'SELECT bugs.*, users.username as assigned_to_name FROM bugs LEFT JOIN users ON bugs.assigned_to = users.id WHERE file_path = ? ORDER BY severity, line_number',
        (original_filename,)
    ).fetchall()
    conn.close()

    return render_template('results.html', filename=original_filename, results=results)

@app.route('/bugs')
def bugs_list():
    status_filter = request.args.get('status', '')
    severity_filter = request.args.get('severity', '')
    language_filter = request.args.get('language', '')
    search_query = request.args.get('search', '')

    conn = get_db_connection()

    # Build the query with filters
    query = '''
        SELECT bugs.*, users.username as assigned_to_name 
        FROM bugs 
        LEFT JOIN users ON bugs.assigned_to = users.id
        WHERE 1=1
    '''
    params = []

    if status_filter:
        query += ' AND bugs.status = ?'
        params.append(status_filter)

    if severity_filter:
        query += ' AND bugs.severity = ?'
        params.append(severity_filter)

    if language_filter:
        query += ' AND bugs.language = ?'
        params.append(language_filter)

    if search_query:
        query += ' AND (bugs.message LIKE ? OR bugs.file_path LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY bugs.created_at DESC'

    bugs = conn.execute(query, params).fetchall()

    # Get filter options
    statuses = conn.execute('SELECT DISTINCT status FROM bugs').fetchall()
    severities = conn.execute('SELECT DISTINCT severity FROM bugs').fetchall()
    languages = conn.execute('SELECT DISTINCT language FROM bugs').fetchall()

    conn.close()

    return render_template(
        'bugs.html', 
        bugs=bugs, 
        statuses=statuses,
        severities=severities,
        languages=languages,
        current_status=status_filter,
        current_severity=severity_filter,
        current_language=language_filter,
        search_query=search_query
    )

@app.route('/bugs/bulk-delete', methods=['GET', 'POST'])
def bulk_delete_bugs():
    if request.method == 'POST':
        bug_ids = request.form.getlist('bug_ids')
        
        if not bug_ids:
            flash('No bugs selected for deletion')
            return redirect(url_for('bugs_list'))
        
        conn = get_db_connection()
        
        # Delete related records for all selected bugs
        for bug_id in bug_ids:
            # Delete comments
            conn.execute('DELETE FROM bug_comments WHERE bug_id = ?', (bug_id,))
            
            # Delete history
            conn.execute('DELETE FROM bug_history WHERE bug_id = ?', (bug_id,))
            
            # Delete tag associations
            conn.execute('DELETE FROM bug_tags WHERE bug_id = ?', (bug_id,))
            
            # Delete suggested fixes
            conn.execute('DELETE FROM suggested_fixes WHERE bug_id = ?', (bug_id,))
        
        # Delete the bugs
        placeholders = ','.join(['?'] * len(bug_ids))
        conn.execute(f'DELETE FROM bugs WHERE id IN ({placeholders})', bug_ids)
        
        conn.commit()
        conn.close()
        
        flash(f'Successfully deleted {len(bug_ids)} bug(s)')
        return redirect(url_for('bugs_list'))

    # GET request - show the bulk delete page
    conn = get_db_connection()
    bugs = conn.execute(
        'SELECT bugs.*, users.username as assigned_to_name FROM bugs LEFT JOIN users ON bugs.assigned_to = users.id ORDER BY bugs.created_at DESC'
    ).fetchall()
    conn.close()

    return render_template('bulk_delete.html', bugs=bugs)

@app.route('/bug/<int:bug_id>')
def bug_detail(bug_id):
    conn = get_db_connection()
    bug = conn.execute(
        'SELECT bugs.*, users.username as assigned_to_name FROM bugs LEFT JOIN users ON bugs.assigned_to = users.id WHERE bugs.id = ?', 
        (bug_id,)
    ).fetchone()

    if not bug:
        flash('Bug not found')
        return redirect(url_for('bugs_list'))

    # Get ONLY the specific AI fix suggestions for this bug
    fixes = conn.execute(
        'SELECT * FROM suggested_fixes WHERE bug_id = ?',
        (bug_id,)
    ).fetchall()

    # If no AI fixes exist for this bug, generate one automatically
    if not fixes:
        # For pasted code, we need to extract the code from the database
        if bug['file_path'].startswith('pasted_code_'):
            # Try to get from session
            code_snippet = session.get('last_analyzed_code', '')
        else:
            # For uploaded files, extract code context from the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], bug['file_path'])
            code_snippet = ai_code_fixer.extract_code_context(file_path, bug['line_number'])
        
        # Generate the AI fix
        if code_snippet:
            ai_fix = ai_code_fixer.generate_fix(
                code_snippet=code_snippet,
                error_message=bug['message'],
                language=bug['language'],
                line_number=bug['line_number']
            )
            
            # Store the AI fix in the database
            conn.execute(
                'INSERT INTO suggested_fixes (bug_id, language, suggestion, code_example) VALUES (?, ?, ?, ?)',
                (bug_id, bug['language'], ai_fix['suggestion'], ai_fix['code_example'])
            )
            conn.commit()
            
            # Refresh the fixes list
            fixes = conn.execute(
                'SELECT * FROM suggested_fixes WHERE bug_id = ?',
                (bug_id,)
            ).fetchall()

    # Get comments
    comments = conn.execute(
        'SELECT bug_comments.*, users.username FROM bug_comments JOIN users ON bug_comments.user_id = users.id WHERE bug_id = ? ORDER BY created_at',
        (bug_id,)
    ).fetchall()

    # Get history
    history = conn.execute(
        'SELECT bug_history.*, users.username FROM bug_history LEFT JOIN users ON bug_history.user_id = users.id WHERE bug_id = ? ORDER BY created_at DESC',
        (bug_id,)
    ).fetchall()

    # Get tags
    tags = conn.execute(
        'SELECT tags.* FROM tags JOIN bug_tags ON tags.id = bug_tags.tag_id WHERE bug_tags.bug_id = ?',
        (bug_id,)
    ).fetchall()

    # Get all available tags for the dropdown
    all_tags = conn.execute('SELECT * FROM tags ORDER BY name').fetchall()

    # Get all users for assignment dropdown
    users = conn.execute('SELECT * FROM users ORDER BY username').fetchall()

    conn.close()

    return render_template(
        'bug_detail.html', 
        bug=bug, 
        fixes=fixes, 
        comments=comments, 
        history=history,
        tags=tags,
        all_tags=all_tags,
        users=users
    )

@app.route('/bug/<int:bug_id>/update', methods=['POST'])
def update_bug(bug_id):
    status = request.form.get('status')
    assigned_to = request.form.get('assigned_to')
    severity = request.form.get('severity')

    conn = get_db_connection()
    bug = conn.execute('SELECT * FROM bugs WHERE id = ?', (bug_id,)).fetchone()

    if not bug:
        flash('Bug not found')
        return redirect(url_for('bugs_list'))

    current_user = get_current_user()
    current_time = datetime.now().isoformat()

    # Update bug status if provided
    if status and status != bug['status']:
        conn.execute(
            'UPDATE bugs SET status = ?, updated_at = ? WHERE id = ?',
            (status, current_time, bug_id)
        )
        log_bug_history(bug_id, current_user['id'], 'status', bug['status'], status)

    # Update assigned user if provided
    if assigned_to:
        assigned_to_id = int(assigned_to) if assigned_to != 'none' else None
        if assigned_to_id != bug['assigned_to']:
            conn.execute(
                'UPDATE bugs SET assigned_to = ?, updated_at = ? WHERE id = ?',
                (assigned_to_id, current_time, bug_id)
            )
            log_bug_history(bug_id, current_user['id'], 'assigned_to', bug['assigned_to'], assigned_to_id)

    # Update severity if provided
    if severity and severity != bug['severity']:
        conn.execute(
            'UPDATE bugs SET severity = ?, updated_at = ? WHERE id = ?',
            (severity, current_time, bug_id)
        )
        log_bug_history(bug_id, current_user['id'], 'severity', bug['severity'], severity)

    conn.commit()
    conn.close()

    flash('Bug updated successfully')
    return redirect(url_for('bug_detail', bug_id=bug_id))

@app.route('/bug/<int:bug_id>/comment', methods=['POST'])
def add_comment(bug_id):
    comment = request.form.get('comment')

    if not comment:
        flash('Comment cannot be empty')
        return redirect(url_for('bug_detail', bug_id=bug_id))

    current_user = get_current_user()

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO bug_comments (bug_id, user_id, comment, created_at) VALUES (?, ?, ?, ?)',
        (bug_id, current_user['id'], comment, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    flash('Comment added successfully')
    return redirect(url_for('bug_detail', bug_id=bug_id))

@app.route('/bug/<int:bug_id>/tag', methods=['POST'])
def add_tag(bug_id):
    tag_id = request.form.get('tag_id')

    if not tag_id:
        flash('No tag selected')
        return redirect(url_for('bug_detail', bug_id=bug_id))

    conn = get_db_connection()

    # Check if tag already exists for this bug
    existing = conn.execute(
        'SELECT * FROM bug_tags WHERE bug_id = ? AND tag_id = ?',
        (bug_id, tag_id)
    ).fetchone()

    if not existing:
        conn.execute(
            'INSERT INTO bug_tags (bug_id, tag_id) VALUES (?, ?)',
            (bug_id, tag_id)
        )
        conn.commit()
        
        # Log the tag addition
        tag = conn.execute('SELECT name FROM tags WHERE id = ?', (tag_id,)).fetchone()
        current_user = get_current_user()
        log_bug_history(bug_id, current_user['id'], 'tag', None, tag['name'])

    conn.close()

    flash('Tag added successfully')
    return redirect(url_for('bug_detail', bug_id=bug_id))

@app.route('/bug/<int:bug_id>/tag/<int:tag_id>/remove', methods=['POST'])
def remove_tag(bug_id, tag_id):
    conn = get_db_connection()

    # Get tag name for history
    tag = conn.execute('SELECT name FROM tags WHERE id = ?', (tag_id,)).fetchone()

    conn.execute(
        'DELETE FROM bug_tags WHERE bug_id = ? AND tag_id = ?',
        (bug_id, tag_id)
    )
    conn.commit()

    # Log the tag removal
    current_user = get_current_user()
    log_bug_history(bug_id, current_user['id'], 'tag', tag['name'], None)

    conn.close()

    flash('Tag removed successfully')
    return redirect(url_for('bug_detail', bug_id=bug_id))

@app.route('/bug/<int:bug_id>/delete', methods=['POST'])
def delete_bug(bug_id):
    conn = get_db_connection()

    # Check if bug exists
    bug = conn.execute('SELECT * FROM bugs WHERE id = ?', (bug_id,)).fetchone()
    if not bug:
        flash('Bug not found')
        return redirect(url_for('bugs_list'))

    # Delete related records first (to maintain referential integrity)
    # Delete comments
    conn.execute('DELETE FROM bug_comments WHERE bug_id = ?', (bug_id,))
            
    # Delete history
    conn.execute('DELETE FROM bug_history WHERE bug_id = ?', (bug_id,))

    # Delete tag associations
    conn.execute('DELETE FROM bug_tags WHERE bug_id = ?', (bug_id,))
    
    # Delete suggested fixes
    conn.execute('DELETE FROM suggested_fixes WHERE bug_id = ?', (bug_id,))

    # Finally delete the bug itself
    conn.execute('DELETE FROM bugs WHERE id = ?', (bug_id,))

    conn.commit()
    conn.close()

    flash('Bug successfully deleted')
    return redirect(url_for('bugs_list'))

@app.route('/api/bugs')
def api_bugs():
    conn = get_db_connection()
    bugs = conn.execute(
        'SELECT bugs.*, users.username as assigned_to_name FROM bugs LEFT JOIN users ON bugs.assigned_to = users.id ORDER BY bugs.created_at DESC'
    ).fetchall()
    conn.close()

    # Convert to list of dicts
    bugs_list = [dict(bug) for bug in bugs]
    return jsonify(bugs_list)

@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    stats = {
        'total': conn.execute('SELECT COUNT(*) FROM bugs').fetchone()[0],
        'by_severity': {
            'critical': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "critical"').fetchone()[0],
            'high': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "high"').fetchone()[0],
            'medium': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "medium"').fetchone()[0],
            'low': conn.execute('SELECT COUNT(*) FROM bugs WHERE severity = "low"').fetchone()[0]
        },
        'by_status': {
            'open': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "open"').fetchone()[0],
            'in_progress': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "in_progress"').fetchone()[0],
            'fixed': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "fixed"').fetchone()[0],
            'closed': conn.execute('SELECT COUNT(*) FROM bugs WHERE status = "closed"').fetchone()[0]
        },
        'by_language': {}
    }

    # Get language distribution
    lang_dist = conn.execute(
        'SELECT language, COUNT(*) as count FROM bugs GROUP BY language'
    ).fetchall()

    for lang in lang_dist:
        stats['by_language'][lang['language']] = lang['count']

    conn.close()
    return jsonify(stats)

@app.route('/export/bugs', methods=['GET'])
def export_bugs():
    format_type = request.args.get('format', 'json')

    conn = get_db_connection()
    bugs = conn.execute(
        'SELECT bugs.*, users.username as assigned_to_name FROM bugs LEFT JOIN users ON bugs.assigned_to = users.id ORDER BY bugs.created_at DESC'
    ).fetchall()
    conn.close()

    # Convert to list of dicts
    bugs_list = [dict(bug) for bug in bugs]

    if format_type == 'json':
        return jsonify(bugs_list)
    elif format_type == 'csv':
        # Create CSV content
        csv_content = "id,file_path,language,line_number,column_number,message,type,severity,status,assigned_to,created_at,updated_at\n"
        for bug in bugs_list:
            csv_content += f"{bug['id']},{bug['file_path']},{bug['language']},{bug['line_number']},{bug['column_number']},\"{bug['message']}\",{bug['type']},{bug['severity']},{bug['status']},{bug.get('assigned_to_name', '')},{bug['created_at']},{bug['updated_at']}\n"
        
        return csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=bugs_export.csv'
        }
    else:
        flash('Unsupported export format')
        return redirect(url_for('bugs_list'))

@app.route('/search')
def search():
    query = request.args.get('q', '')

    if not query:
        return render_template('search_results.html', query='', results=[])

    conn = get_db_connection()
    results = conn.execute(
        '''
        SELECT bugs.*, users.username as assigned_to_name 
        FROM bugs 
        LEFT JOIN users ON bugs.assigned_to = users.id
        WHERE bugs.message LIKE ? OR bugs.file_path LIKE ? OR bugs.type LIKE ?
        ORDER BY bugs.created_at DESC
        ''',
        (f'%{query}%', f'%{query}%', f'%{query}%')
    ).fetchall()
    conn.close()

    return render_template('search_results.html', query=query, results=results)

@app.route('/toggle-ai-suggestions', methods=['POST'])
def toggle_ai_suggestions():
    """Toggle AI suggestions on/off"""
    app.config['ENABLE_AI_SUGGESTIONS'] = not app.config['ENABLE_AI_SUGGESTIONS']
    status = 'enabled' if app.config['ENABLE_AI_SUGGESTIONS'] else 'disabled'
    flash(f'AI-powered fix suggestions {status}')
    return redirect(request.referrer or url_for('dashboard'))

if __name__ == '__main__':
    # Make sure database exists
    os.makedirs('database', exist_ok=True)

    # Always check if the database needs to be initialized or updated
    init_db()

    app.run(debug=True, host='0.0.0.0', port=8080)

