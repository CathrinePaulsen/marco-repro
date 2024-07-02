import pandas as pd

from rq5.utils import bcolors
from rq6.utils import RESOURCES, get_pairwise_result


def process():
    READ_FROM = RESOURCES / "raw" / "compcheck_corrected.csv"
    WRITE_TO = RESOURCES / "processed" / READ_FROM.name

    df = pd.read_csv(READ_FROM)
    num_rows = df.shape[0]
    print(f"[READ {READ_FROM}] Number of rows: {num_rows}")

    # Add evaluation column
    df["MaRCo evaluation"] = None
    # Remove duplicate upgrades
    processed_df = df.drop_duplicates(subset=["Library", "Old Version", "New Version"])

    num_rows = processed_df.shape[0]
    print(f"[WRITE {WRITE_TO}] Number of rows: {num_rows}")
    processed_df.to_csv(WRITE_TO, index=False)


def evaluate():
    READ_FROM = RESOURCES / "processed" / "compcheck_corrected.csv"
    WRITE_TO = RESOURCES / "evaluated" / "compcheck_corrected_parent.csv"

    df = pd.read_csv(READ_FROM)
    num_rows = df.shape[0]
    print(f"[READ {READ_FROM}] Number of rows: {num_rows}")
    count = 0

    try:
        for index, row in df.iterrows():
            count += 1
            ga = row['Library']
            old_version = row['Old Version']
            new_version = row['New Version']
            marco_evaluation = row['MaRCo evaluation']

            if pd.isna(marco_evaluation):  # Evaluate row if it as not yet been evaluated
                print(f"Getting result of row {index}: {ga}:{old_version}=>{new_version}")
                result = get_pairwise_result(ga, old_version, new_version)
                print(bcolors.OKBLUE + f"Result={result}" + bcolors.ENDC)
                df.at[index, 'MaRCo evaluation'] = result
                df.to_csv(WRITE_TO, index=False)

            print(bcolors.OKGREEN + f"== PROGRESS {int(count / num_rows * 100)}% ({count} / {num_rows})" +
                  bcolors.ENDC)

        num_rows = df.shape[0]
        print(f"[WRITE {WRITE_TO}] Number of rows: {num_rows}")
        df.to_csv(WRITE_TO, index=False)
    except KeyboardInterrupt as e:
        print(e)
        print(f"[WRITE {WRITE_TO}] Number of rows: {num_rows}")
        df.to_csv(WRITE_TO, index=False)
        print(bcolors.OKGREEN + f"== PROGRESS {int(count / num_rows * 100)}% ({count} / {num_rows})" + bcolors.ENDC)

