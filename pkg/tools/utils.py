import argparse
import logging
from random import Random

from .crawler_util import *
from .time_util import *


def init_loging_config():
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _logger = logging.getLogger("MediaCrawler")
    _logger.setLevel(level)
    return _logger


logger = init_loging_config()

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def get_random_str(random_len: int = 12) -> str:
    """
    获取随机字符串
    :param random_len:
    :return:
    """
    random_str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    _random = Random()
    for i in range(random_len):
        random_str += chars[_random.randint(0, length)]
    return random_str