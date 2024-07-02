import argparse

from rq6 import uppdatera, ranger, compcheck


def main():
    parser = argparse.ArgumentParser(description='Script for evaluating RQ6.')
    parser.add_argument('-d', '--dataset', choices=['uppdatera', 'ranger', 'compcheck'],
                        help='Specify which dataset you would like to use.',
                        required=True)
    parser.add_argument('-m', '--mode', choices=['process', 'evaluate'],
                        help='Specify whether to process or evaluate the dataset.',
                        required=True)
    args = parser.parse_args()
    dataset = args.dataset
    mode = args.mode

    if mode == 'evaluate':
        if dataset == 'uppdatera':
            input("Evaluating Uppdatera dataset. Press any key to continue.")
            uppdatera.evaluate()
        elif dataset == 'ranger':
            input("Evaluating Ranger dataset. Press any key to continue.")
            ranger.evaluate_manually_adjusted()
        elif dataset == 'compcheck':
            input("Evaluting CompCheck dataset. Press any key to continue.")
            compcheck.evaluate()

    elif mode == 'process':
        if dataset == 'uppdatera':
            input("Processing Uppdatera dataset. Press any key to continue.")
            uppdatera.process()
        elif dataset == 'ranger':
            input("Processing Ranger dataset. Press any key to continue.")
            ranger.process()
        elif dataset == 'compcheck':
            input("Processing CompCheck dataset. Press any key to continue.")
            compcheck.process()

