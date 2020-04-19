import mysql.connector as dblib
import argparse


# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", 
                    type=str,
                    default="localhost",
                    help="Host on which database is running")
    parser.add_argument("--port", 
                    type=str,
                    default="3306",
                    help="Database port")
    parser.add_argument("--user", 
                    type=str,
                    default="kafka",
                    help="Database user")
    parser.add_argument("--password", 
                    type=str,
                    default="my-secret-pw",
                    help="Database password")
    args=parser.parse_args()
    return args


def init_db(db_user, db_password, db_host, db_port):

    # 
    # Create database connection
    #
    c = dblib.connect(user=db_user, 
                    password=db_password,
                    host=db_host,
                    port=db_port,
                    database='kafka')
    # 
    # Open cursor
    #
    cursor = c.cursor()

    #
    # Now create all tablesWe first try to drop the tables
    # if it exists
    #
    try:
        cursor.execute('''DROP TABLE accounts''')
    except dblib.Error as err:
        pass
    try:
        cursor.execute('''DROP TABLE offsets''')
    except dblib.Error as err:
        pass
    try:
        cursor.execute('''DROP TABLE sequence_no''')
    except dblib.Error as err:
        pass

    #
    # Note that partition is a reserved name in MySQL
    #
    cursor.execute('''CREATE TABLE offsets
                (part INT, offset INT)''')
    cursor.execute('''CREATE TABLE accounts
                (id INT, balance INT)''')
    cursor.execute('''CREATE TABLE sequence_no
                (current INT)''')

    # 
    # Insert a few records
    # 
    accounts = [(0, 0),
                (1, 100)]

    # 
    # Be careful - MySQL uses %s as parameter markes, while SQLLite3
    # uses ?. We therefore use the marker determined above
    sqlString =  '''INSERT INTO accounts
                        (id, balance)
                    VALUES (%s,%s)'''
    cursor.executemany(sqlString, accounts)
    sqlString =  '''INSERT INTO sequence_no
                        (current)
                    VALUES (0)'''
    cursor.execute(sqlString)


    # and commit
    c.commit()


def main():
    #
    # Read arguments
    #
    args=get_args()

    #
    # Prepare database
    #
    init_db(args.user, args.password, args.host, args.port)

    
main()