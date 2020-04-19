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
    for table in ['accounts', 'offsets', 'sequence_no', 'consumed']:
        try:
            cursor.execute('''DROP TABLE %s''' % table)
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
                (last_used INT)''')
    cursor.execute('''CREATE TABLE consumed
                (part INT, last INT)''')

    # 
    # Insert a few records
    # 
    accounts = [(0, 0),
                (1, 100)]
    consumed = [(0,0), (1,0)]
    offsets = [(0,0), (1,0)]

    # 
    # Be careful - MySQL uses %s as parameter markes, while SQLLite3
    # uses ?. We therefore use the marker determined above
    sqlString =  '''INSERT INTO accounts
                        (id, balance)
                    VALUES (%s,%s)'''
    cursor.executemany(sqlString, accounts)
    sqlString =  '''INSERT INTO sequence_no
                        (last_used)
                    VALUES (0)'''
    cursor.execute(sqlString)
    sqlString =  '''INSERT INTO consumed
                        (part, last)
                    VALUES (%s, %s)'''
    cursor.executemany(sqlString, consumed)
    sqlString =  '''INSERT INTO offsets
                        (part, offset)
                    VALUES (%s, %s)'''
    cursor.executemany(sqlString, offsets)



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