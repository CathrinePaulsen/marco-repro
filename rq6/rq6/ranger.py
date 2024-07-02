from pathlib import Path

import pandas as pd

from core import get_available_versions
from rq5.utils import bcolors
from rq6.utils import RESOURCES, Result
from server import find_compatibility_results
from server.exceptions import (BaseJarNotFoundException, CandidateJarNotFoundException, MavenNoPomInDirectoryException,
                               MavenSurefireTestFailedException, GithubRepoNotFoundException,
                               MavenCompileFailedException,
                               GithubTagNotFoundException, BaseMavenCompileTimeout, MavenResolutionFailedException)


def unroll_range(range: str, available_versions: list[str]) -> list[str]:
    """Given a range [lower,upper], use available_versions to unroll the range into a list of versions"""
    lower_bound, upperbound = range[1:-1].split(",")
    versions = []
    in_range = False
    for version in available_versions:
        if upperbound == version:
            in_range = True
        if lower_bound == version:
            in_range = False
            versions.append(version)
        if in_range:
            versions.append(version)

    return versions


def merge_csv():
    files = [f"cleaned_ranger_level_{x}.csv" for x in range(1, 11)]
    WRITE_TO = RESOURCES / "processed" / f"ranger_merged.csv"
    dfs = [pd.read_csv(RESOURCES / "processed" / "intermediate" / file) for file in files]
    df = pd.concat(dfs).reset_index(drop=True)
    df.drop_duplicates(inplace=True)
    grouped = df.groupby('gav')['compatible_versions'].agg(sum)
    df = grouped.reset_index()
    df['compatible_versions (ours)'] = None
    df['err'] = None
    df.to_csv(WRITE_TO, index=False)
    num_rows = df.shape[0]
    print("Number of rows:", num_rows)


def clean_csv(filename: str):
    READ_FROM = RESOURCES / "raw" / filename
    WRITE_TO = RESOURCES / "processed" / "intermediate" / f"cleaned_{filename}"

    df = pd.read_csv(READ_FROM)
    num_rows = df.shape[0]
    print("READ Number of rows:", num_rows)
    df = df.drop(columns=['project', 'project_depth'])
    df.drop_duplicates(inplace=True)
    df = df[df['status'] == 'success']
    df = df.drop(columns=['status', 'Incompatibility', 'No suitable version', 'Error (no jar, call graph)'])
    df['dep'] = df['dep'].apply(lambda x: x.replace("|", ":"))

    for index, row in df.iterrows():
        g, a, v = row['dep'].split(":")
        range = row['dep_range']
        versions = unroll_range(range, get_available_versions(g, a))
        df.at[index, 'dep_range'] = versions

    grouped = df.groupby('dep')['dep_range'].agg(sum)
    df = grouped.reset_index()
    df = df.rename(columns={'dep': 'gav', 'dep_range': 'compatible_versions'})

    num_rows = df.shape[0]
    print("WRITE Number of rows:", num_rows)
    df.to_csv(WRITE_TO, index=False)


def adjust_csv(read_from: Path, write_to: Path):
    df = pd.read_csv(read_from)
    num_rows = df.shape[0]
    print("READ Number of rows:", num_rows)

    df[['GA', 'version']] = df['gav'].str.rsplit(':', n=1, expand=True)
    df.insert(loc=0, column='GA', value=df.pop('GA'))
    df.insert(loc=1, column='version', value=df.pop('version'))
    df = df.drop(columns=['gav'])

    for index, row in df.iterrows():
        compatible_versions = row['compatible_versions (ours)']
        if not pd.isna(compatible_versions):
            compatible_list = pd.eval(compatible_versions)
            compatible_list.append(row['version'])
            df.at[index, 'compatible_versions (ours)'] = compatible_list

    num_rows = df.shape[0]
    print("WRITE Number of rows:", num_rows)
    df.to_csv(write_to, index=False)


def process():
    for level in range(1, 11):
        filename = f"ranger_level_{level}.csv"
        clean_csv(filename)
        # adjust_csv(filename)
        # input()
    merge_csv()

def evaluate_manually_adjusted():
    READ_FROM = RESOURCES / "processed" / 'ranger_manually_adjusted.csv'
    WRITE_TO = RESOURCES / "evaluated" / 'ranger_manually_adjusted.csv'

    df = pd.read_csv(READ_FROM)
    total = df.shape[0]
    count = 0

    try:
        for index, row in df.iterrows():
            count += 1
            g, a = row['GA'].split(":")
            v = row['version']
            github_link = row['github_link']
            to_evaluate = not pd.isna(row['github_link'])

            if to_evaluate:
                print(f"Getting result of row {index}: {g}:{a}:{v}")
                try:
                    compat_result = find_compatibility_results(g, a, v, silent=True, github_link=github_link)
                    result = [x.v_cand for x in compat_result if x.dynamically_compatible and x.statically_compatible]
                    print(bcolors.OKGREEN + f"Result={result}" + bcolors.ENDC)
                    df.at[index, 'compatible_versions (ours)'] = str(result)
                except MavenNoPomInDirectoryException as e:
                    print(e)
                    err = Result.NO_MAVEN
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except MavenResolutionFailedException as e:
                    print(e)
                    err = Result.NO_RESOLVE
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except (MavenCompileFailedException, BaseMavenCompileTimeout) as e:
                    print(e)
                    err = Result.NO_COMPILE
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except GithubRepoNotFoundException as e:
                    print(e)
                    err = Result.NO_GITHUB_LINK
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except GithubTagNotFoundException as e:
                    print(e)
                    err = Result.NO_GITHUB_TAG
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except MavenSurefireTestFailedException as e:
                    print(e)
                    err = Result.NO_TEST
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except (BaseJarNotFoundException, CandidateJarNotFoundException) as e:
                    print(e)
                    err = Result.NO_JAR
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err

                df.to_csv(WRITE_TO, index=False)
            print(bcolors.OKGREEN + f"== PROGRESS [{g}:{a}:{v}] {int(count / total * 100)}% ({count} / {total})" +
                  bcolors.ENDC)

    except KeyboardInterrupt as e:
        print(e)
        df.to_csv(WRITE_TO, index=False)
        print(bcolors.OKGREEN + f"== PROGRESS {int(count / total * 100)}% ({count} / {total})" + bcolors.ENDC)


def evaluate():
    READ_FROM = RESOURCES / "processed" / 'ranger_merged.csv'
    WRITE_TO = RESOURCES / "evaluated" / 'ranger_parent.csv'
    WRITE_TO_ADJUSTED = RESOURCES / "evaluated" / 'ranger_parent_adjusted.csv'

    df = pd.read_csv(READ_FROM)
    total = df.shape[0]
    count = 0

    try:
        for index, row in df.iterrows():
            count += 1
            g, a, v = row['gav'].split(":")
            evaluated = not pd.isna(row['compatible_versions (ours)']) or not pd.isna(row['err'])

            if not evaluated:
                print(f"Getting result of row {index}: {g}:{a}:{v}")
                try:
                    compat_result = find_compatibility_results(g, a, v, silent=True)
                    result = [x.v_cand for x in compat_result if x.dynamically_compatible and x.statically_compatible]
                    print(bcolors.OKGREEN + f"Result={result}" + bcolors.ENDC)
                    df.at[index, 'compatible_versions (ours)'] = str(result)

                except MavenNoPomInDirectoryException as e:
                    print(e)
                    err = Result.NO_MAVEN
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except MavenResolutionFailedException as e:
                    print(e)
                    err = Result.NO_RESOLVE
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except (MavenCompileFailedException, BaseMavenCompileTimeout) as e:
                    print(e)
                    err = Result.NO_COMPILE
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except GithubRepoNotFoundException as e:
                    print(e)
                    err = Result.NO_GITHUB_LINK
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except GithubTagNotFoundException as e:
                    print(e)
                    err = Result.NO_GITHUB_TAG
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except MavenSurefireTestFailedException as e:
                    print(e)
                    err = Result.NO_TEST
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err
                except (BaseJarNotFoundException, CandidateJarNotFoundException) as e:
                    print(e)
                    err = Result.NO_JAR
                    print(bcolors.FAIL + f"Err={err}" + bcolors.ENDC)
                    df.at[index, 'err'] = err

                df.to_csv(WRITE_TO, index=False)
            print(bcolors.OKGREEN + f"== PROGRESS [{row['gav']}] {int(count / total * 100)}% ({count} / {total})" +
                  bcolors.ENDC)

    except KeyboardInterrupt as e:
        print(e)
        df.to_csv(WRITE_TO, index=False)
        print(bcolors.OKGREEN + f"== PROGRESS {int(count / total * 100)}% ({count} / {total})" + bcolors.ENDC)
        adjust_csv(read_from=WRITE_TO, write_to=WRITE_TO_ADJUSTED)

    adjust_csv(read_from=WRITE_TO, write_to=WRITE_TO_ADJUSTED)
