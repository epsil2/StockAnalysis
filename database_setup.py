import sqlite3

def create_table():
    conn = sqlite3.connect('stocks.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT NOT NULL,
            date DATETIME NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()