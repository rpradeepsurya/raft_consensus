import sqlite3

connection = sqlite3.connect("user.db")
records = connection.execute("select * from USER")

print("=====================")
print("   Records from DB     ")
print("=====================")
print()

for data in records:
    print(f'id: {data[0]}  name: {data[1]}  email: {data[2]} \n')