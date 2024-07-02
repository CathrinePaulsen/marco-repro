# Processed datasets

## CompCheck
* `compcheck_corrected.csv`: Result of processing `raw/compcheck_corrected.csv`, used for evaluation. Added column 'MaRCo evaluation" and dropped rows with duplicate values for the 3-tuple ('Library', 'Old Version', 'New Version').


## Uppdatera
* `uppdatera.csv`: Result of processing `raw/uppdatera`, used for evaluation. Column 'MaRCo evaluation' added.

* `uppdatera_with_github_links.csv`: Result of processing `raw/uppdatera_with_github_links.csv `, used for evaluation. Column 'MaRCo evaluation' added.


## Ranger
* `ranger_merged.csv`: The merged result of processing all `raw/ranger_level_{x}.csv` files, used for evaluation.
