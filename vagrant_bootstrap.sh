#!/usr/bin/env bash
sudo docker run --name redis-cache -p 6379:6379 --restart always -d redis redis-server --appendonly yes
sudo docker run --name myyear_dev -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_USER=pyyear -e MYSQL_PASSWORD=pyyear -e MYSQL_DATABASE=myyear_dev --restart always -d mysql