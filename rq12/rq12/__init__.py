import argparse

from rq12.generate_trees import generate_trees
from rq12.get_projects import collect_projects
from rq12.get_deps import get_resolved_dependencies, get_projects_with_tree
from rq12.get_direct_transitives import get_direct_transitives
from rq12.get_managed import get_managed
from rq12.get_results import get_results


def confirm(step: str):
    input(f"[RQ12-MAIN] Running collection step {step}. Press any key to begin.")


def main():
    parser = argparse.ArgumentParser(description='Script that collects the datapoints used to evaluate RQ1-2.')
    parser.add_argument('-s', '--step', choices=['projects', 'trees', 'dependencies', 'transitives', 'managed',
                                                 'results'],
                        help='Specify which collection step in the data collection pipeline you would like to run. '
                             'Options (in logical order): projects, trees, dependencies, transitives, managed, results',
                        required=True)

    args = parser.parse_args()
    collection_step = args.step

    confirm(collection_step)
    if collection_step == 'projects':
        # Got 800 projects from API, left with 362 with poms
        collect_projects()
    elif collection_step == 'trees':
        # Successfully generated trees for 327 projects
        generate_trees()
    elif collection_step == 'dependencies':
        # Successfully extracted 12949 dependencies from verbose dependency trees, and 1726 conflicts
        get_resolved_dependencies()
    elif collection_step == 'transitives':
        get_direct_transitives()
    elif collection_step == 'managed':
        get_managed()
    elif collection_step == 'results':
        get_results()
