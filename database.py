# Use SQLite to save info in a database and load data when the application is opened, relational database
# Use DB Browser for SQLite to visualize the database
import sqlite3
import typing

class WorkspaceData:
    def __init__(self):
        # Connect to the database
        self.conn = sqlite3.connect("database.db")
        # When data is received from database, return list of SQLite row objects (accessible like python dictionaries)
        self.conn.row_factory = sqlite3.Row

        # Cursor object to make queries to the database
        self.cursor = self.conn.cursor()

        # Table for data to store (one for watchlist and one for strategies)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT, exchange TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS strategies (strategy_type TEXT, contract TEXT,"
                            "timeframe TEXT, balance_pct REAL, take_profit REAL, stop_loss REAL, extra_params TEXT)")

        # Commit changes or they won't be saved
        self.conn.commit()


    # Delete the previous table content and record new data in it
    def save(self, table: str, data: typing.List[typing.Tuple]):
        # Each tuple is a row to insert in the database table
        # Each element in the tuple is a value for a column in the row
        # Delete previous content of the table
        self.cursor.execute(f"DELETE FROM {table}")

        # "INSERT INTO watchlist (symbol, exchange) VALUE(?, ?)"

        # Get list of columns for the table
        table_data = self.cursor.execute(f"SELECT * FROM {table}")

        # Loop through the description attribute of the cursor that is returned by the above statement
        # Creates a list of columns because description is a list of tuples and the column name is the first element of
        # each tuple
        columns = [description[0] for description in table_data.description]

        # Join method converts list of columns into a string where each element is separated by a comma,
        sql_statement = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"

        # Insert rows
        self.cursor.executemany(sql_statement, data)
        self.conn.commit()

    # Get data from table - get all the rows recorded for the table
    def get(self, table: str) -> typing.List[sqlite3.Row]:
        # Execute SQL statement to get all the rows of the table
        self.cursor.execute(f"SELECT * FROM {table}")
        data = self.cursor.fetchall()

        return data


