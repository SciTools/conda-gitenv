#!/usr/bin/env python

from __future__ import print_function
import argparse

import conda_env_tracker.resolve as resolve
import conda_env_tracker.tag_dates as tag_dates
import conda_env_tracker.label_tag as label_tag
import conda_env_tracker.deploy as deploy

    
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='Manage conda environments through git repos')

    resolve.configure_parser(subparsers.add_parser('resolve'))
    tag_dates.configure_parser(subparsers.add_parser('autotag'))
    label_tag.configure_parser(subparsers.add_parser('autolabel'))
    deploy.configure_parser(subparsers.add_parser('deploy'))

    args = parser.parse_args()
    return args.function(args)


if __name__ == '__main__':
    main()
