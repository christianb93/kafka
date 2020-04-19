#
# This script will start a Docker container running a MySQL database
# It will then create a user kafka with password my-secret-pw 
# and a database kafka 
#


# Start docker container
docker run -d --name kafka-mysql \
           --rm \
           -p 3306:3306 \
           -e MYSQL_ROOT_PASSWORD=my-secret-root-pw \
           -e MYSQL_USER=kafka \
           -e MYSQL_PASSWORD=my-secret-pw \
            mysql 

#
# Wait until container is up
#
found=0
while [ "$found" == "0" ]; do
  found=$(docker ps | grep kafka-mysql | wc -l )
  sleep 1
done
 
# Give the database some time to come up
docker exec -it kafka-mysql \
           mysqladmin --user=root --password=my-secret-root-pw \
           --host='127.0.0.1'  \
            --silent status
 
while [ $? == 1  ]
do
  sleep 5
  docker exec -it kafka-mysql \
             mysqladmin --user=root --password=my-secret-root-pw \
             --host='127.0.0.1'  \
             --silent status
done
 
# Create database kafka and grant rights to user kafka
docker exec -it kafka-mysql \
          mysqladmin --user=root \
          --password=my-secret-root-pw \
          --host='127.0.0.1'  create kafka
docker exec  -it kafka-mysql \
          mysql --user=root \
          --password=my-secret-root-pw \
          --host='127.0.0.1' kafka \
          -e "grant all on kafka.* to kafka;"
