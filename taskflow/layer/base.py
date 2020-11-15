

class BaseLayer:
    """ """

    def __len__(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    async def run(self, *args, **kwargs):
        raise NotImplementedError

    async def stop(self):
        raise NotImplementedError

    def locale(self):
        raise NotImplementedError
