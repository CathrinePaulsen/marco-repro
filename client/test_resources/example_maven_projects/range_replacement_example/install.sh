cd libB-v1
mvn clean install
cd ..

cd libB-v2
mvn clean install
cd ..

cd libA
mvn clean install
cd ..

cd libC
mvn clean install
cd ..

cd app
mvn clean install
