#
# This script will start a Docker container running a MySQL database
# It will then create a user kafka with password my-secret-pw 
# and a database kafka 
#


# Start docker container
docker run -d --name some-mysql \
           --rm \
           -p 3306:3306 \
           -e MYSQL_ROOT_PASSWORD=my-secret-root-pw \
           -e MYSQL_USER=kafka \
           -e MYSQL_PASSWORD=my-secret-pw \
            mysql 
 
# Give the database some time to come up
mysqladmin --user=root --password=my-secret-root-pw \
           --host='127.0.0.1'  \
            --silent status
 
while [ $? == 1  ]
do
  sleep 5
  mysqladmin --user=root --password=my-secret-root-pw \
             --host='127.0.0.1'  \
             --silent status
done
 
# Create database kafka and grant rights to user kafka
mysqladmin --user=root \
           --password=my-secret-root-pw \
            --host='127.0.0.1'  create kafka
echo 'grant all on kafka.* to 'kafka';' \
              | mysql --user=root \
                      --password=my-secret-root-pw \
                      --host='127.0.0.1' kafka