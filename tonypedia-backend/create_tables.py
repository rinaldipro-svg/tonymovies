from database import engine, Base
import models

print("Building tables in Railway PostgreSQL...")

# This command looks at models.py and creates the tables if they don't exist yet
Base.metadata.create_all(bind=engine)

print("✅ SUCCESS! Tables are created and ready for data.")