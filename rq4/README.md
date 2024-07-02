# rq4

## Install
`pip install -e rq4` from root

## Usage
The package has two entrypoints: 
- `rq4-breaking`: collects and evaluates the breaking dataset (based on the BUMP benchmark)
- `rq4-non-breaking`: to collects and evaluates the non-breaking dataset (based on dependabot PRs)

### Non-breaking entrypoint
```
$ rq4-non-breaking --help
usage: rq4-non-breaking [-h] -s {projects,prs,links,static,dynamic} [--stats_only]

Script that collects the datapoints for the non-breaking dataset used to evaluate RQ4.

options:
  -h/--help            show this help message and exit
  
  -s/--step {projects,prs,static,links,dynamic}
                        Specify which collection step in the data collection pipeline 
                        you would like to run. Options (in logical order): 
                            projects, prs, static, links, dynamic.
                        
  --stats_only          Enable stats-only mode, use this if you only want to print
                        the statistics associated with a particular collection step.
```


### Breaking entrypoint
```
$ rq4-breaking --help
usage: rq4-breaking [-h] -s {clean,static,link,dynamic} [--stats_only]

Script that collects the datapoints for the breaking dataset used to evaluate RQ4.

options:
  -h/--help            show this help message and exit
  
  -s/--step {clean,static,link,dynamic}
                        Specify which collection step in the data collection pipeline 
                        you would like to run. Options (in logical order): 
                            clean, static, link, dynamic.
                        
  --stats_only          Enable stats-only mode, use this if you only want to print 
                        the statistics associated with a particular collection step.

```