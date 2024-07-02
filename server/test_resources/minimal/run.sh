#!/bin/zsh

cd dep-4
mvn clean install
cd ..

cd dep-3
mvn clean install
cd ..

cd dep-2
mvn clean install
cd ..

cd dep-1
mvn clean install
cd ..

cd app
mvn clean install
mvn dependency:tree -Dverbose





