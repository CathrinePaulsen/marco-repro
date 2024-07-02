### Replacing soft constraints with versions example

#### Problem setup
* Run `cleanup_local.sh` to delete the dependencies installed in .m2.
* Run `install.sh` to install the dependencies in local .m2.
* Run `run.sh` to run the application.

Example 1 (below): Conflicting transitive version collisions; tool can help convert potential runtime errors into buildtime errors.

Example 2 (todo): Compatible transitive version collisions where lowest version is resolved; tool can help get fresher dependencies.
```
          App
       /       \
    LibA:1   LibC:3
      |        |
    LibB:2   LibB:1 
    
$ mvn dependency:tree -Dverbose
[INFO] com.example.app:app:jar:1
[INFO] +- com.example.libA:libA:jar:1:compile
[INFO] |  \- com.example.libB:libB:jar:2:compile
[INFO] \- com.example.libC:libC:jar:1:compile
[INFO]    \- (com.example.libB:libB:jar:1:compile - omitted for conflict with 2)
```

Passes build, while dependency:tree reports that AppB v1 was ommitted for conflict with AppB v2.
Consider that AppB v1 is not forwards compatible with AppB v2, then running App may result in runtime failure.

App calls `LibA.method(String)` and `LibC.method(String)`.
`LibA.method(String)` in turn calls `LibB.method(String, Integer)`,
while `LibC.method(String)` calls `LibB.method(String)`.
In other words, the method signature has changed between LibB v2 and LibB v1.

This results in a runtime failure when LibC tries to call `LibB.method` with the wrong parameters since LibB v2 was 
resolved which expects different parameters than what LibC is providing.

Build will pass, and the version conflict will cause runtime issues.

#### Repairing the POM with the client tool
Given the following compatibility mapping:
```
Compatibility Mapping: 
{
    "com.example.libB:libB:1": [
        "1"
    ],
    "com.example.libB:libB:2": [
        "2"
    ],
    "com.example.libA:libA:1": [
        "1"
    ],
    "com.example.libC:libC:1": [
        "1"
    ]
}
```

```
Repository structure:

maven_repository/
├── com
│   └── example
│       └── libB
│           └── libB
│               ├── 1
│               │   ├── libB-1.jar
│               │   └── libB-1.pom
│               └── 2
│                   ├── libB-2.jar
│                   └── libB-2.pom
└── ... etc
```

Adding the repository to app's POM now results in build failure instead of run failure:
```
<repositories>
    <repository>
      <id>local-maven-repo</id>
      <url>http://127.0.0.1:5000/maven/</url>
    </repository>
  </repositories>
  
[INFO] ------------------------< com.example.app:app >-------------------------
[INFO] Building app 1
[INFO]   from pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  0.124 s
[INFO] Finished at: 2024-02-20T17:52:31+01:00
[INFO] ------------------------------------------------------------------------
[ERROR] Failed to execute goal on project app: Could not resolve dependencies for project com.example.app:app:jar:1: Failed to collect dependencies for com.example.app:app:jar:1: Could not resolve version conflict among [com.example.libA:libA:jar:[1,1] -> com.example.libB:libB:jar:[2,2], com.example.libC:libC:jar:[1,1] -> com.example.libB:libB:jar:[1,1]] -> [Help 1]


```