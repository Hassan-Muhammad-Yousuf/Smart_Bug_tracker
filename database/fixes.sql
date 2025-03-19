-- Drop existing table if it exists
DROP TABLE IF EXISTS suggested_fixes;

-- Create the table
CREATE TABLE suggested_fixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bug_id INTEGER NOT NULL,
    language TEXT,
    suggestion TEXT NOT NULL,
    code_example TEXT,
    FOREIGN KEY (bug_id) REFERENCES bugs (id)
);

-- Generic fixes (bug_id = 0)
INSERT INTO suggested_fixes (bug_id, language, suggestion, code_example)
VALUES 
    -- Python fixes
    (0, 'python', 'Use list comprehension instead of map/filter for better readability', 
    '# Before:
numbers = [1, 2, 3, 4]
squared = list(map(lambda x: x**2, numbers))

# After:
numbers = [1, 2, 3, 4]
squared = [x**2 for x in numbers]'),

    (0, 'python', 'Use context manager for file operations to ensure proper resource cleanup', 
    '# Before:
f = open("file.txt", "r")
content = f.read()
f.close()

# After:
with open("file.txt", "r") as f:
    content = f.read()'),

    (0, 'python', 'Add docstrings to improve code documentation and maintainability', 
    '# Before:
def calculate_area(radius):
    return 3.14 * radius * radius

# After:
def calculate_area(radius):
    """Calculate the area of a circle given its radius.
    
    Args:
        radius: The radius of the circle
        
    Returns:
        The area of the circle
    """
    return 3.14 * radius * radius'),

    (0, 'python', 'Remove unused imports to improve code readability and performance', 
    '# Before:
import os
import sys
import json  # Unused import

print("Hello World")

# After:
import os
import sys

print("Hello World")'),

    (0, 'python', 'Use f-strings for string formatting in Python 3.6+', 
    '# Before:
name = "John"
age = 30
message = "My name is {} and I am {} years old".format(name, age)

# After:
name = "John"
age = 30
message = f"My name is {name} and I am {age} years old"'),

    (0, 'python', 'Use enumerate() when you need both index and value from an iterable', 
    '# Before:
fruits = ["apple", "banana", "cherry"]
for i in range(len(fruits)):
    print(f"{i}: {fruits[i]}")

# After:
fruits = ["apple", "banana", "cherry"]
for i, fruit in enumerate(fruits):
    print(f"{i}: {fruit}")'),

    -- JavaScript fixes
    (0, 'javascript', 'Use let or const instead of var for better scoping', 
    '// Instead of:
var x = 10;
var y = 20;

// Use:
const x = 10;  // For values that won''t change
let y = 20;    // For values that might change'),

    (0, 'javascript', 'Use === instead of == for strict equality comparison', 
    '// Instead of:
if (x == null) {
    // code
}

// Use:
if (x === null) {
    // code
}

// Or if you want to check for null or undefined:
if (x === null || x === undefined) {
    // code
}

// Or more concisely:
if (x == null) { // This is actually okay for null/undefined checks
    // code
}'),

    (0, 'javascript', 'Remove console.log statements in production code', 
    '// Instead of leaving console.log statements:
function calculate() {
    console.log("Calculating...");
    return x + y;
}

// Either remove them:
function calculate() {
    return x + y;
}

// Or use a logging utility that can be disabled in production:
function calculate() {
    logger.debug("Calculating...");
    return x + y;
}'),

    (0, 'javascript', 'Avoid using alert() in production code', 
    '// Instead of:
function showError() {
    alert("An error occurred!");
}

// Use:
function showError() {
    // Use a modal component or toast notification
    showErrorModal("An error occurred!");
    // Or
    showToast("An error occurred!", "error");
}'),

    (0, 'javascript', 'Use arrow functions for cleaner syntax and lexical this binding', 
    '// Instead of:
function multiply(a, b) {
    return a * b;
}

// Use:
const multiply = (a, b) => a * b;

// For preserving this context:
// Instead of:
function Counter() {
    this.count = 0;
    this.interval = setInterval(function() {
        this.count++; // this is not Counter instance!
    }, 1000);
}

// Use:
function Counter() {
    this.count = 0;
    this.interval = setInterval(() => {
        this.count++; // this is Counter instance
    }, 1000);
}'),

    (0, 'javascript', 'Use template literals for string interpolation', 
    '// Instead of:
const name = "John";
const greeting = "Hello, " + name + "!";

// Use:
const name = "John";
const greeting = `Hello, ${name}!`;'),

    -- Java fixes
    (0, 'java', 'Use private fields with getters and setters for better encapsulation', 
    '// Before:
public class Person {
    public String name;
    public int age;
}

// After:
public class Person {
    private String name;
    private int age;
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public int getAge() {
        return age;
    }
    
    public void setAge(int age) {
        this.age = age;
    }
}'),

    (0, 'java', 'Add null checks to prevent NullPointerException', 
    '// Before:
public void processString(String input) {
    int length = input.length();
    // process string
}

// After:
public void processString(String input) {
    if (input == null) {
        return; // or throw an exception
    }
    int length = input.length();
    // process string
}'),

    (0, 'java', 'Use try-with-resources for automatic resource management', 
    '// Before:
BufferedReader reader = null;
try {
    reader = new BufferedReader(new FileReader("file.txt"));
    String line = reader.readLine();
    // process line
} catch (IOException e) {
    e.printStackTrace();
} finally {
    try {
        if (reader != null) {
            reader.close();
        }
    } catch (IOException e) {
        e.printStackTrace();
    }
}

// After:
try (BufferedReader reader = new BufferedReader(new FileReader("file.txt"))) {
    String line = reader.readLine();
    // process line
} catch (IOException e) {
    e.printStackTrace();
}'),

    (0, 'java', 'Use StringBuilder for string concatenation in loops', 
    '// Before:
String result = "";
for (int i = 0; i < 100; i++) {
    result += i;  // Creates a new String object each time
}

// After:
StringBuilder result = new StringBuilder();
for (int i = 0; i < 100; i++) {
    result.append(i);
}
String finalResult = result.toString();'),

    (0, 'java', 'Use enhanced for loop (for-each) for cleaner iteration', 
    '// Before:
List<String> names = Arrays.asList("Alice", "Bob", "Charlie");
for (int i = 0; i < names.size(); i++) {
    String name = names.get(i);
    System.out.println(name);
}

// After:
List<String> names = Arrays.asList("Alice", "Bob", "Charlie");
for (String name : names) {
    System.out.println(name);
}'),

    -- C++ fixes
    (0, 'cpp', 'Always free dynamically allocated memory to prevent memory leaks', 
    '// Before:
void processData() {
    int* data = new int[100];
    // process data
    // missing delete
}

// After:
void processData() {
    int* data = new int[100];
    // process data
    delete[] data;
}'),

    (0, 'cpp', 'Use smart pointers instead of raw pointers for safer memory management', 
    '// Before:
void processData() {
    int* data = new int[100];
    // process data
    delete[] data;
}

// After:
#include <memory>

void processData() {
    std::unique_ptr<int[]> data(new int[100]);
    // process data
    // no need to delete, memory is automatically managed
}'),

    (0, 'cpp', 'Use const references for function parameters to avoid unnecessary copying', 
    '// Before:
void processVector(std::vector<int> vec) {
    // process vector
}

// After:
void processVector(const std::vector<int>& vec) {
    // process vector
}'),

    (0, 'cpp', 'Use range-based for loops for cleaner iteration (C++11 and later)', 
    '// Before:
std::vector<int> numbers = {1, 2, 3, 4, 5};
for (std::vector<int>::iterator it = numbers.begin(); it != numbers.end(); ++it) {
    std::cout << *it << std::endl;
}

// After:
std::vector<int> numbers = {1, 2, 3, 4, 5};
for (const auto& num : numbers) {
    std::cout << num << std::endl;
}'),

    (0, 'cpp', 'Use nullptr instead of NULL or 0 for null pointers (C++11 and later)', 
    '// Before:
int* ptr = NULL;
if (ptr == 0) {
    // do something
}

// After:
int* ptr = nullptr;
if (ptr == nullptr) {
    // do something
}'),

    -- Go fixes
    (0, 'go', 'Always check and handle errors in Go', 
    '// Before:
func readFile(filename string) []byte {
    data, _ := ioutil.ReadFile(filename)
    return data
}

// After:
func readFile(filename string) ([]byte, error) {
    data, err := ioutil.ReadFile(filename)
    if err != nil {
        return nil, err
    }
    return data, nil
}'),

    (0, 'go', 'Use context for cancellation and timeouts in long-running operations', 
    '// Before:
func fetchData(url string) ([]byte, error) {
    resp, err := http.Get(url)
    // process response
    return nil, nil
}

// After:
func fetchData(ctx context.Context, url string) ([]byte, error) {
    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return nil, err
    }
    resp, err := http.DefaultClient.Do(req)
    // process response
    return nil, nil
}'),

    (0, 'go', 'Use defer for cleanup operations to ensure they are executed', 
    '// Before:
func processFile(filename string) error {
    f, err := os.Open(filename)
    if err != nil {
        return err
    }
    // process file
    f.Close()  // Might not be called if there''s an error during processing
    return nil
}

// After:
func processFile(filename string) error {
    f, err := os.Open(filename)
    if err != nil {
        return err
    }
    defer f.Close()  // Will be called when function returns
    // process file
    return nil
}'),

    (0, 'go', 'Use named return values for clearer documentation', 
    '// Before:
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}

// After:
func divide(a, b float64) (result float64, err error) {
    if b == 0 {
        err = errors.New("division by zero")
        return
    }
    result = a / b
    return
}'),

    (0, 'go', 'Use struct embedding for composition over inheritance', 
    '// Before:
type Logger struct {
    logLevel int
}

func (l *Logger) Log(message string) {
    fmt.Println(message)
}

type App struct {
    logger Logger
    name   string
}

func (a *App) Log(message string) {
    a.logger.Log(message)
}

// After:
type Logger struct {
    logLevel int
}

func (l *Logger) Log(message string) {
    fmt.Println(message)
}

type App struct {
    Logger  // Embedded struct
    name string
}

// Now App has Log method automatically');

