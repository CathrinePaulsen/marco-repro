# Example 1

```
                 app
               /     \
          appA         appB:1
           |
          appB:2
```

* There is a SoftVer conflict between `appB:1` and `appB:2`
* Maven resolves `appB:1`, which is problematic if `appB:1` is not forwards compatible with `appB:2`


```
                 app
               /     \
          appA         appB:[1,2]
           |
          appB:2
```
* Say we applied the tool to `app`'s POM, which replaced `appB:1` with `app:[1,2]`
* Maven now resolves `appB:2`. However, Maven does so simply because it is the highest version in the range.
* => NO PROBLEM.
  * How is `appB:2` reported in dependency:tree? "` - omitted for duplicate`"
  * dependencyConvergence plugin: `pass`
```
                 app
               /     \
          appA         appB:[1,3]
           |
          appB:2
```
* Say we applied the tool to `app`'s POM, which replaced `appB:1` with `app:[1,3]`
* Maven now resolves `appB:3`, which is a problem if `appB:2` is not forwards compatible with `appB:3`.
* => PROBLEM.
  * How is `appB:2` reported in dependency:tree? "` - omitted for conflict with 3`"
  * dependencyConvergence plugin: `fail`
  * What happens if the range is `[1],[3]`?
  
```
                 app
               /     \
          appA         appB:[1],[3]
           |
          appB:2
```
* Maven resolves `appB:3`.
* => PROBLEM same as above.
  * How is `appB:2` reported in dependency:tree? "` - omitted for conflict with 3`"
  * dependencyConvergence plugin: `fail`
### Problem
When using ranges, Maven will simply resolve the highest version in the (overlapping) range.
Any transitive version constraints declared as SoftVer are simply ignored ...

### Solution
Gather all softver conflicts. Add them as direct dependencies. Replace SoftVer with range. Then resolve.

```
                 app                                     app
               /     \                              /     |      \
          appA         appB:[1,3]       =>      appA   appB:[2]   appB:[1,3]
           |                                     |
          appB:2                                appB:2

```
```xml
  <dependencies>
    <dependency>
      <groupId>com.example.appA</groupId>
      <artifactId>appA</artifactId>
      <version>1</version>
    </dependency>

    <dependency>
      <groupId>com.example.appB</groupId>
      <artifactId>appB</artifactId>
      <version>[1,3]</version>
    </dependency>
    
    <dependency>
      <groupId>com.example.appB</groupId>
      <artifactId>appB</artifactId>
      <version>[2]</version>
    </dependency>
  </dependencies>
```
* Maven now resolves `appB:[2]`. However, the order matters. Maven ignores all duplicate constraints except the one defined last.

### Problem
Cannot simply generate range for each softver, then insert all constraints in the POM.
This means it also does not catch conflicting ranges.

### Solution?
We would need to determine the overlapping range ourselves...................................
1. Each softver maps to a set of compatible versions.
2. Find the intersection between the compatible version sets to find the overlapping compatible versions.
   If the intersection is empty then there is no solution and build should fail. Quit. Else continue.
3. If the intersection is non-empty, convert the list of compatible versions to a range.
   1. Sort versions following Mavens algorithm (where?)
   2. Make range with the first version as lower boundary and the last version as upper boundary
   3. List the versions in the version range using Maven VersionRange? Exclude any versions listed in range but not in compatible versions.
   

... simply merging ranges won't work. I need to consider backwards/forwards compatibility.
If there is a softver conflict, some dependency versions will get upgraded and some downgraded. 
Both directions need to be considered safe.


### Problem?
The enforcer plugin ensures that the declared versions converge to the same.
Wouldn't this solve SoftVer versions not being caught at build time? Making at least one part of the tool moot.
https://maven.apache.org/enforcer/enforcer-rules/dependencyConvergence.html

With plugin the below errors, whereas without it would pass build.
```
                 app
               /     \
          appA         appB:[1] or 1
           |
          appB:2

[ERROR] Rule 0: org.apache.maven.enforcer.rules.dependency.DependencyConvergence failed with message:
[ERROR] Failed while enforcing releasability.
[ERROR]
[ERROR] Dependency convergence error for com.example.appB:appB:jar:2 paths to dependency are:
[ERROR] +-com.example.app:app:jar:1
[ERROR]   +-com.example.appA:appA:jar:1:compile
[ERROR]     +-com.example.appB:appB:jar:2:compile
[ERROR] and
[ERROR] +-com.example.app:app:jar:1
[ERROR]   +-com.example.appB:appB:jar:1:compile
[ERROR]

                 app
               /     \
          appA         appC:1
           |            |
          appB:2       appB:1

[ERROR] Dependency convergence error for com.example.appB:appB:jar:2 paths to dependency are:
[ERROR] +-com.example.app:app:jar:1
[ERROR]   +-com.example.appA:appA:jar:1:compile
[ERROR]     +-com.example.appB:appB:jar:2:compile
[ERROR] and
[ERROR] +-com.example.app:app:jar:1
[ERROR]   +-com.example.appC:appC:jar:1:compile
[ERROR]     +-com.example.appB:appB:jar:1:compile
```

The enforcer plugin should ensure that there is build failure if there are softver conflicts present.
Can we use the enforcer plugin to enforce a set of ranges? ehhhh I mean sure but... that's not the point anyway.
It could however be used to verify that a softver conflict is indeed present.


Can possibly use this plugin setup to check / enforce that for the specific dependency, the resolved version is in the range.
But if declaring as direct dependency... that's guaranteed anyway...

```
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-enforcer-plugin</artifactId>
                <version>3.4.1</version>
                <executions>
                    <execution>
                        <id>enforce</id>
                        <configuration>
                            <rules>
                                <dependencyConvergence>
                                    <excludes>
                                        <exclude>*</exclude>
                                    </excludes>
                                    <includes>
                                        <include>com.fasterxml.jackson.core:jackson-databind:[2.13.4,2.13.5),[2.14.0]</include>
                                    </includes>
                                </dependencyConvergence>
                            </rules>
                        </configuration>
                        <goals>
                            <goal>enforce</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
```





Make plugin that goes in between the resolution process...?
If I could just control the output of getVersionConstraint...?
https://maven.apache.org/resolver/apidocs/org/eclipse/aether/graph/DefaultDependencyNode.html#getVersionConstraint()