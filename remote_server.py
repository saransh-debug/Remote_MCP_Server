import sqlite3
from unicodedata import category
from fastmcp import FastMCP
import os 

mcp = FastMCP(name="Expense Tracker")

DB_PATH=os.path.join(os.path.dirname(__file__),"expense.db")
FILE_PATH=os.path.join(os.path.dirname(__file__),"expenses_json.json")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT DEFAULT '',
        note TEXT DEFAULT ''
    )
""")


init_db()

@mcp.tool
def add_expense(date , amount , category , subcategory="",note=""):
    with sqlite3.connect(DB_PATH) as c :
        c.execute('''
    INSERT INTO expenses(date,amount,category,subcategory,note) VALUES(?,?,?,?,?)
''',(date,amount,category,subcategory,note))

@mcp.tool
def list_expenses(start_Date , end_Date):
    ''' gives the list of expenses between two dates '''
    with sqlite3.connect(DB_PATH) as c :
       cur =  c.execute("SELECT * FROM expenses BETWEEN ? AND ? ORDER BY id ASC",(start_Date , end_Date))
       cols =[ d[0] for d in cur.description ]
       return [dict(zip(cols,r)) for r in cur.fetchall()] # zip here combines one row's data with one columns values [("id", 1),("date", "2026-09-20"),("amount", 200),("category", "Food"),("subcategory", "Lunch"),("note", "Subway") kind of this then dict turns it into dictionary 

@mcp.tool
def summarise(start_Date ,end_Date,category=None):
    "summarises the expenses according to category or without category"
    with sqlite3.connect(DB_PATH) as c :
        if category:
            cur = c.execute("SELECT SUM(amount) as total FROM expenses WHERE date BETWEEN ? AND ? AND category=? GROUP BY category",(start_Date,end_Date,category))
        else:
            cur = c.execute("SELECT SUM(amount) as total FROM expenses WHERE date BETWEEN ? AND ?",(start_Date,end_Date))
        return cur.fetchone()[0] or 0
         

@mcp.resource("expense://categories",mime_type="application/json") # it tells the mcp that here i have some resources of your use , you can check it out 
def categories():
    "read fresh each time so that you can name the file categories more accruately."
    with open(FILE_PATH,"r",encoding="utf-8") as f: #there is a file which helps the host and client to choose a specific name to save in the database of the expense , and to prevent the irregularity in the names saves in the database of the expenses
        return f.read()

@mcp.resource("info://server")
def about_server():
    "Get information about the server" 

    return {
        "name": "Expense Tracker",
        "version": "1.0.0",
        "description": "An MCP server that helps you track your expenses smartly.",
        "transport": "HTTP",
        "host": "0.0.0.0",
        "port": 8000,
        "tools": [
           "add_expense",
            "list_expenses",
            "summarise"
        ],
        "resources": [
            "info://server",
            "expense://categories"
        ]
    }


if __name__ == "__main__":
    mcp.run(transport="http",host="0.0.0.0",port=8000)