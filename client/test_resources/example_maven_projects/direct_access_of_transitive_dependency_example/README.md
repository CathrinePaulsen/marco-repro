### AppA (Directly accesses transitive dependency)

Depends on AppB, which depends on AppC.

Directly calls methods from both AppB and AppC without declaring AppC as a direct dependency.

```
       AppA
      /    \
    AppB   [AppC should've been declared here]
      |
    AppC
```

```
$ mvn dependency:analyze -DoutputXML

[WARNING] Used undeclared dependencies found:
[WARNING]    com.example.appC:appC:jar:1:compile
[INFO] Add the following to your pom to correct the missing dependencies:
[INFO]
<dependency>
  <groupId>com.example.appC</groupId>
  <artifactId>appC</artifactId>
  <version>1</version>
</dependency>


```