

from argparse import ArgumentParser
from config import SERVER_CONFIG


if __name__ == '__main__':
    # parser = ArgumentParser()
    # parser.add_argument('s', help='服务名称', type=str)
    # args = parser.parse_args()

    # 启动服务
    server = SERVER_CONFIG['taskflow']
    __import__(server['module']).main.main()
