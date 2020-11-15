

def get_client(name):
    """ 获取服务的SDK客户端。"""
    module = getattr(__import__(f'client.{name}'), name)
