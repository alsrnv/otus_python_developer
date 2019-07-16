

import argparse
import os
import json
import logging
import re
import datetime
from collections import namedtuple

FILE_LOG = namedtuple('FILE_LOG', {'name':'', 'date':'', 'ext':''})

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname).1s %(message)s",
                    datefmt="%Y.%m.%d %H:%M:%S",
                    filename=None)

LOG_PATTERN = re.compile(
    r"(?P<remote_addr>[\d\.]+)\s"
    r"(?P<remote_user>\S*)\s+"
    r"(?P<http_x_real_ip>\S*)\s"
    r"\[(?P<time_local>.*?)\]\s"
    r'"(?P<request>.*?)"\s'
    r"(?P<status>\d+)\s"
    r"(?P<body_bytes_sent>\S*)\s"
    r'"(?P<http_referer>.*?)"\s'
    r'"(?P<http_user_agent>.*?)"\s'
    r'"(?P<http_x_forwarded_for>.*?)"\s'
    r'"(?P<http_X_REQUEST_ID>.*?)"\s'
    r'"(?P<http_X_RB_USER>.*?)"\s'
    r"(?P<request_time>\d+\.\d+)\s*"
)

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


def get_latest_log_file(path_to_dir):
    logging.info('Starting to search latest file')
    pattern = re.compile(r"^nginx-access-ui\.log-(\d{8})(\.gz)?$")
    min_date = datetime.datetime.min.date()
    file_output = None
    for file_name in os.listdir(path_to_dir):
        match = pattern.search(file_name)
        if match:
            file_date = datetime.datetime.strptime(match.group(1), "%Y%m%d").date()
            file_ext = match.group(2)
            if file_date > min_date:
                min_date = file_date
                file_output = FILE_LOG(name=file_name, date=file_date, ext=file_ext)
    return file_output

def process_line(line):
    m = LOG_PATTERN.match(line)
    if m:
        return m.groupdict()
    return None




def main():

    try:
        args = process_args()
        config = combine_config(path_to_config_file=args.config_path)
        logging.info("Config is {}".format(config))
        file_latest = get_latest_log_file(config['LOG_DIR'])
        logging.info("Latest log file is {}".format(file_latest))
        if not file_latest:
            raise Exception('Нет файлов для обработки')
        print(file_latest.name)




    except Exception as e:
        logging.exception(str(e))


if __name__ == "__main__":
    main()
