#!/bin/bash
# Script used to deploy artifacts of a Maven project to the local repository.
# Use --jar to deploy an external jar

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 (--all|--jar) /path/to/your/other/project/pom.xml [jar_path groupId artifactId version]"
    exit 1
fi

deploy_type="$1"
pom_path="$2"

if [ "$deploy_type" = "--all" ]; then
    # Run mvn deploy
    mvn deploy \
        -f "$pom_path" \
        -Durl=http://127.0.0.1:5000/maven/ \
        -DaltDeploymentRepository=local-repo::http://127.0.0.1:5000/maven \
        -DrepositoryId=local-repo
elif [ "$deploy_type" = "--jar" ]; then
    if [ "$#" -ne 6 ]; then
        echo "Usage: $0 --jar /path/to/your/other/project/pom.xml jar_path groupId artifactId version"
        exit 1
    fi

    jar_path="$3"
    g="$4"
    a="$5"
    v="$6"

    # Verify that $pom_path ends with pom.xml
    if [[ ! "$pom_path" =~ pom.xml$ ]]; then
        echo "Error: \$pom_path must end with pom.xml."
        exit 1
    fi

     # Verify that $jar_path ends with .jar
    if [[ ! "$jar_path" =~ \.jar$ ]]; then
        echo "Error: \$jar_path must end with .jar."
        exit 1
    fi

    # Run mvn deploy-file
    mvn deploy:deploy-file \
        -DgroupId="$g" -DartifactId="$a" -Dversion="$v"  \
        -DpomFile="$pom_path" \
        -Dfile="$jar_path" \
        -Durl=http://127.0.0.1:5000/maven/ \
        -DaltDeploymentRepository=local-repo::http://127.0.0.1:5000/maven \
        -DrepositoryId=local-repo
else
    echo "Invalid option. Use --all or --jar."
    exit 1
fi
