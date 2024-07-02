# Raw datasets

## CompCheck
* `compcheck.csv`: Original "[CompCheck] Incompatible Client-Lib Pairs" dataset obtained from [the CompCheck paper](https://sites.google.com/view/compcheck) [1].
* `compcheck_corrected.csv`: Data used for processing, after manually correcting rows. Two rows were removed for incomplete version information, 18 rows had malformed versions corrected of the pattern: version "X" was given but does not exist, however version "X.0" exists.

## Uppdatera
* `uppdatera.csv`: Original table translated from Table 3 in [2, p.9].

* `uppdatera_with_github_links.csv`: Original table with an added column with the GitHub links for each library. The GitHub links were obtained by googling "github" followed by the GA. The repository's pomfile was then inspected to see whether it matches the GA.

## Ranger
* `ranger_level_X.csv`: Original "RQ4 Ecosystem Evaluation" dataset files obtained from [the Ranger paper](https://sites.google.com/view/ase23maven/dataset?authuser=0), [3]. 


## References
- [1] C. Zhu, M. Zhang, X. Wu, X. Xu, and Y. Li, “Client-Specific Upgrade Compatibility Checking via Knowledge-Guided Discovery,” ACM Trans. Softw. Eng. Methodol., vol. 32, no. 4, pp. 1–31, Oct. 2023, doi: 10.1145/3582569.
- [2] J. Hejderup and G. Gousios, “Can we trust tests to automate dependency updates? A case study of Java projects,” in Journal of Systems and Software, Elsevier, 2022, p. 111097. doi: [https://doi.org/10.1016/j.jss.2021.111097]().
- [3] L. Zhang et al., “Mitigating Persistence of Open-Source Vulnerabilities in Maven Ecosystem,” in 2023 38th IEEE/ACM International Conference on Automated Software Engineering (ASE), Luxembourg, Luxembourg: IEEE, Sep. 2023, pp. 191–203. doi: 10.1109/ASE56229.2023.00058.

