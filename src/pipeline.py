"""Command-line entry point. Run from the repository root."""
import argparse

def main():
    parser=argparse.ArgumentParser(description='Mérida Urban Intelligence pipeline')
    parser.add_argument('step',choices=['etl','load','analyze','all'])
    args=parser.parse_args()
    if args.step in ['etl','all']:
        from .transform import build_processed
        build_processed()
    if args.step in ['load','all']:
        from .load import run_load
        run_load()
    if args.step in ['analyze','all']:
        from .analysis import run_analysis
        run_analysis()

if __name__=='__main__':main()
