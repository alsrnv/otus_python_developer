

import argparse
import json
import logging
import re
import datetime
from collections import namedtuple, defaultdict
import os
import gzip
from statistics import median
import string

FILE_LOG = namedtuple('FILE_LOG', {'name':'', 'date':'', 'ext':'', 'path_to_file':''})

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
    "LOG_DIR": "./log",
    "ERROR_PERCENT": 0.4
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
                file_output = FILE_LOG(name=file_name, date=file_date, ext=file_ext,
                                       path_to_file = os.path.join(path_to_dir, file_name))
    return file_output

def process_line(line):
    match = LOG_PATTERN.match(line)
    if match:
        return match.groupdict()
    return None


def read_file(file_log, error_percent):
    logging.info("Обработка файла {}".format(file_log.name))
    if file_log.ext == '.gz':
        f = gzip.open(file_log.path_to_file, mode='rt')
    else:
        f = file_log.path_to_file.open()
    n_lines = 0
    n_errors = 0
    dict_url = defaultdict(list)
    with f:
        for line in f:
            n_lines += 1
            res_dict = process_line(line)
            if res_dict is None:
                n_errors += 1
                continue
            try:
                url = res_dict['request'].split()[1]
                dict_url[url].append(float(res_dict['request_time']))
            except(ValueError, TypeError, IndexError):
                continue
    if n_errors/n_lines > error_percent:
        raise Exception("Доля ошибок превысила допустимый пределел {}".format(error_percent))
    return dict_url

def compute_stat(dict_url, report_size):
    total_times = 0
    total_count = 0
    for _, v in dict_url.items():
        total_times += sum(v)
        total_count += len(v)

    stat = []
    for url, request_times in dict_url.items():
        stat.append({
            'url': url,
            'count': len(request_times),
            'count_perc': round(100. * len(request_times) / float(total_count), 3),
            'time_sum': round(sum(request_times), 3),
            'time_perc': round(100. * sum(request_times) / total_times, 3),
            'time_avg': round(sum(request_times)/len(request_times), 3),
            'time_max': round(max(request_times), 3),
            "time_med": round(median(request_times), 3),
        })
    stat = sorted(stat, key = lambda x: x['time_sum'], reverse=True)
    stat = stat[:report_size]
    return stat

def get_report_path(report_dir, file_log):
    report_name = 'report-{}.html'.format(file_log.date.strftime(format='%Y.%m.%d'))
    report_path = os.path.join(report_dir, report_name)
    return report_path

def create_report(report_dir, report_path, stat):
    template_path = os.path.join(report_dir, 'report.html')
    with open(template_path) as f:
        template = string.Template(f.read())
    report = template.safe_substitute(table_json=json.dumps(stat))
    with open(report_path, mode='w') as f:
        f.write(report)
    logging.info("Отчет {} создан".format(report_path))


def main():
    args = process_args()
    config = combine_config(path_to_config_file=args.config_path)
    logging.info("Config is {}".format(config))
    file_log_latest = get_latest_log_file(config['LOG_DIR'])
    logging.info("Latest log file is {}".format(file_log_latest))
    if not file_log_latest:
        raise FileNotFoundError('Нет файлов для обработки')
    dict_url_raw = read_file(file_log_latest, error_percent=config['ERROR_PERCENT'])
    stat = compute_stat(dict_url=dict_url_raw, report_size=config['REPORT_SIZE'])
    report_path = get_report_path(report_dir=config['REPORT_DIR'], file_log=file_log_latest)
    if os.path.exists(report_path):
        logging.info("Отчет {} уже существует".format(report_path))
        return
    create_report(report_dir=config['REPORT_DIR'], report_path=report_path, stat=stat)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(str(e))
