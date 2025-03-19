DROP TABLE IF EXISTS bugs;
DROP TABLE IF EXISTS suggested_fixes;
DROP TABLE IF EXISTS bug_comments;
DROP TABLE IF EXISTS bug_history;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS bug_tags;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Insert default user
INSERT INTO users (username, email, created_at) 
VALUES ('admin', 'admin@example.com', datetime('now'));

CREATE TABLE bugs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL,
  language TEXT NOT NULL,
  line_number INTEGER NOT NULL,
  column_number INTEGER NOT NULL,
  message TEXT NOT NULL,
  type TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  assigned_to INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (assigned_to) REFERENCES users (id)
);

CREATE TABLE suggested_fixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id INTEGER NOT NULL,
    language TEXT,
    symbol TEXT,
    suggestion TEXT NOT NULL,
    code_example TEXT,
    FOREIGN KEY (bug_id) REFERENCES bugs (id)
);

CREATE TABLE bug_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  comment TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (bug_id) REFERENCES bugs (id),
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE bug_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_id INTEGER NOT NULL,
  user_id INTEGER,
  field_changed TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (bug_id) REFERENCES bugs (id),
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  color TEXT NOT NULL
);

-- Insert some default tags
INSERT INTO tags (name, color) VALUES 
  ('frontend', '#3498db'),
  ('backend', '#2ecc71'),
  ('security', '#e74c3c'),
  ('performance', '#f39c12'),
  ('ui', '#9b59b6');

CREATE TABLE bug_tags (
  bug_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (bug_id, tag_id),
  FOREIGN KEY (bug_id) REFERENCES bugs (id),
  FOREIGN KEY (tag_id) REFERENCES tags (id)
);

