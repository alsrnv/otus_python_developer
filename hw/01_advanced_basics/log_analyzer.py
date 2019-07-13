


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


import argparse
import os
import json
import logging


LOCAL_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="config_path")
    args = parser.parse_args()
    if not args.config_path:
        raise argparse.ArgumentError()
    if not os.path.exists(args.config_path):
        raise Exception('Неверный путь файла')
    return args

def combine_config(path_to_config_file, local_config=LOCAL_CONFIG):
    try:
        with open(path_to_config_file) as f:
            config_file = json.load(f)
        return {**local_config, **config_file}
    except (ValueError, TypeError):
        return local_config


def main():
    args = process_args()
    config = combine_config(path_to_config_file=args.config_path)
    print(config)


if __name__ == "__main__":
    main()
