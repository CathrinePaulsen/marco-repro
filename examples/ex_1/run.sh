#!/bin/zsh

cd appB1
mvn clean install
cd ..

cd appB2
mvn clean install
cd ..

cd appB3
mvn clean install
cd ..

cd appA
mvn clean install
cd ..

cd appC
mvn clean install
cd ..

cd app
mvn clean install





