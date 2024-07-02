import pandas as pd

from rq6.utils import RESOURCES, get_pairwise_result


def process():
    READ_FROM = RESOURCES / "raw" / 'uppdatera_with_github_links.csv'
    # READ_FROM = RESOURCES / "raw" / 'uppdatera.csv'
    WRITE_TO = RESOURCES / 'processed' / READ_FROM.name

    df = pd.read_csv(READ_FROM)
    # Add evaluation column
    df["MaRCo evaluation"] = None

    df.to_csv(WRITE_TO, index=False)


def evaluate():
    READ_FROM = RESOURCES / "processed" / 'uppdatera.csv'
    # READ_FROM = RESOURCES / "processed" / 'uppdatera.csv'
    WRITE_TO = RESOURCES / 'evaluated' / 'uppdatera_parent.csv'

    df = pd.read_csv(READ_FROM)

    for index, row in df.iterrows():
        ga = row['GA']
        old_version = row['old version']
        new_version = row['new version']
        # github_repo = row['GA GitHub'] if not pd.isna(row['GA GitHub']) else None
        # print(f"Getting result of row {index}: {ga}:{old_version}=>{new_version} with Github link:{github_repo}")
        result = get_pairwise_result(ga, old_version, new_version)
        input(f"Result={result}")
        df.at[index, 'compatible (ours)'] = result

    df.to_csv(WRITE_TO, index=False)
