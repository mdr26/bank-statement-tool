import psycopg2
import os

conn = psycopg2.connect(os.getenv("DB_URL"))
print("CONNECTED SUCCESSFULLY")