


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


import argparse
import os
import json
import logging
import re
import datetime


logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname).1s %(message)s",
                    datefmt="%Y.%m.%d %H:%M:%S",
                    filename=None)


LOCAL_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def process_args():
    logging.info('Reading parameter config')
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="config_path")
    args = parser.parse_args()
    if not args.config_path:
        raise argparse.ArgumentError()
    if not os.path.exists(args.config_path):
        raise Exception('Неверный путь файла')
    return args

def combine_config(path_to_config_file, local_config=LOCAL_CONFIG):
    logging.info('Combine log files')
    try:
        with open(path_to_config_file) as f:
            config_file = json.load(f)
        return {**local_config, **config_file}
    except (ValueError, TypeError):
        return local_config


def get_latest_file(path_to_dir):
    logging.info('Starting to search latest file')
    pattern = re.compile(r"^nginx-access-ui\.log-(\d{8})(\.gz)?$")
    min_date = datetime.datetime.min.date()
    file_output = None
    for file_name in os.listdir(path_to_dir):
        match = pattern.search(file_name)
        if match:
            file_date = datetime.datetime.strptime(match.group(1), "%Y%m%d").date()
            if file_date > min_date:
                file_output = file_name
                min_date = file_date
    return file_output

def main():
    args = process_args()
    config = combine_config(path_to_config_file=args.config_path)
    logging.info("Config is {}".format(config))
    file_latest = get_latest_file(config['LOG_DIR'])
    logging.info("Latest log file is {}".format(file_latest))







if __name__ == "__main__":
    main()
