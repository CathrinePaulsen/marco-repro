## Example 1: Conflicting SoftVer versions in transitive dependencies

###Motivating Q: How can we detect conflicts where the resolved version is different from the declared SoftVer version?

Given the following dependency tree of declared SoftVers:

```
     A(v1)
  /        \
B(v1)    C(v1)
 |         |
D(v1)    D(v2)
```

There is a dependency conflict between D(v1) and D(v2), but **building A(v1) succeeds despite the fact that there is a conflict between two possibly incompatible versions. This could result in unexpected behavior at runtime which we want to avoid.**

The output of `mvn dependency:tree -Dverbose` shows the Maven mediation:

```
[INFO] --- dependency:3.6.0:tree (default-cli) @ appA ---
[INFO] com.example.appA:appA:jar:1
[INFO] +- com.example.appB:appB:jar:1:compile
[INFO] |  \- com.example.appD:appD:jar:1:compile
[INFO] \- com.example.appC:appC:jar:1:compile
[INFO]    \- (com.example.appD:appD:jar:2:compile - omitted for conflict with 1)
```

...stating that the dependency conflict was detected and v1 was chosen over v2 in mediation.

**Answer:** Search the output of `mvn dependency:tree -Dverbose` for instances of `omitted for conflict with <ver>`.

### Supporting Q: How can we be sure whether the versions involved in the conflict are SoftVer?

It is not possible to tell from the version numbers reported by `mvn dependency:tree` whether the versions are soft or not. Both the soft contraint `<version>2</version>` and the hard constraint `<version>[2]</version` are reported as `2` despite it affecting the mediation process. Following the example above, except `C(v1)->D(v2)` is now a hard constraint, v2 will now be resolved instead of v1:

```
[INFO] --- dependency:3.6.0:tree (default-cli) @ appA ---
[INFO] com.example.appA:appA:jar:1
[INFO] +- com.example.appB:appB:jar:1:compile
[INFO] |  \- (com.example.appD:appD:jar:1:compile - omitted for conflict with 2)
[INFO] \- com.example.appC:appC:jar:1:compile
[INFO]    \- com.example.appD:appD:jar:2:compile
```

However, if both versions in this conflict are instead declared as version ranges (hard constraints), building fails with `DependencyResolutionException`:

```
[ERROR] Failed to execute goal on project appA: Could not resolve dependencies for project com.example.appA:appA:jar:1: Failed to collect dependencies for com.example.appA:appA:jar:1: Could not resolve version conflict among [com.example.appB:appB:jar:1 -> com.example.appD:appD:jar:[1,1], com.example.appC:appC:jar:1 -> com.example.appD:appD:jar:[2,2]] -> [Help 1]
```

**Answer:** if building succeeds but `mvn dependency:tree` reports conflicts, there must be at least one conflicting SoftVer and no conflicting version ranges. It is safe to assume that each occurrence of `omitted for conflict with <ver>` is an instance of a SoftVer constraint being ignored, as conflicting version ranges would result in build failure.

### Supporting Q: What does it look like if there are two overlapping version ranges, and one conflicting SoftVer?
```
                 A(v1) 
  /               |      \
B(v1)           C(v1)   D(v1)
 |                |
D(v1),D(v2)  D(v2),D(v3)
```

```
[INFO] --- dependency:3.6.0:tree (default-cli) @ appA ---
[INFO] com.example.appA:appA:jar:1
[INFO] +- com.example.appB:appB:jar:1:compile
[INFO] |  \- com.example.appD:appD:jar:2:compile
[INFO] +- com.example.appC:appC:jar:1:compile
[INFO] |  \- (com.example.appD:appD:jar:2:compile - omitted for duplicate)
[INFO] \- (com.example.appD:appD:jar:1:compile - omitted for conflict with 2)
```


## Example 2: Conflicting SoftVer versions between direct and transitive dependency

The result of this example is the same as above, included for completion.

Given the following declared dependency tree:

```
     A(v1)
  /        \
D(v1)    C(v1)
           |
         D(v2)
```

There is a dependency conflict between D(v1) and D(v2), but building A(v1) succeeds.

The output of `mvn dependency:tree -Dverbose` shows the Maven mediation:

```
[INFO] --- dependency:3.6.0:tree (default-cli) @ appA ---
[INFO] com.example.appA:appA:jar:1
[INFO] +- com.example.appC:appC:jar:1:compile
[INFO] |  \- (com.example.appD:appD:jar:2:compile - omitted for conflict with 1)
[INFO] \- com.example.appD:appD:jar:1:compile
```
...stating that the dependency conflict was detected and v1 was chosen over v2 in mediation.

Switching the soft contraint `C(v1)->D(v2)` into a hard constraint changes the outcome of the mediation as expected. Now v2 is resolved instead of v1:

```
[INFO] --- dependency:3.6.0:tree (default-cli) @ appA ---
[INFO] com.example.appA:appA:jar:1
[INFO] +- com.example.appC:appC:jar:1:compile
[INFO] |  \- com.example.appD:appD:jar:2:compile
[INFO] \- (com.example.appD:appD:jar:1:compile - omitted for conflict with 2)
```

Again, changing both versions involved in the conflict into hard constraints causes the build to fail.