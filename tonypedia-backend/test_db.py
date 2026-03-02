from database import engine
from sqlalchemy import text

print("Attempting to connect to Railway PostgreSQL...")

try:
    # We open a connection and ask the database what version it is running
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        for row in result:
            print("\n✅ SUCCESS! Connected to the database.")
            print(f"Server Info: {row[0]}\n")
except Exception as e:
    print("\n❌ FAILED to connect.")
    print(f"Error Details: {e}\n")