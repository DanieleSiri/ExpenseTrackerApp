#!/bin/bash
# run this script to run the app modifying the username and password
while [ -z $username ]
do
read -p "Insert username: " username
echo "${username}" | grep '[0-9]' >/dev/null
if [ $? = 0 ]
then
	echo "username can't have numbers"
	exit 1
fi
done

while [ -z $password ]
do
read -p "Insert password: " password
done

sed -i -e "8s/\"[a-zA-Z]*\"/\"${username}\"/" -e "20s/\"[a-zA-Z]*\"/\"${username}\"/" docker-compose.yml
sed -i -e "9s/\"[a-zA-Z0-9]*\"/\"${password}\"/" -e "21s/\"[a-zA-Z0-9]*\"/\"${password}\"/" docker-compose.yml

docker-compose up -d
