import psycopg2

conn = psycopg2.connect(
    dbname="meal_planner_poc",
    user="postgres",
    password="!Eiiey45Romty?",
    host="localhost",
    port=5432
)

cur = conn.cursor()
cur.execute("SELECT id, name, category FROM meals;")
rows = cur.fetchall()

for row in rows:
    print(row)

cur.close()
conn.close()
