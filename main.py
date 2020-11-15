

from pydantic import BaseModel
from abc import ABCMeta
# import api.app

from client import get_client

get_client('api')

class Meta(ABCMeta):
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)

    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        cls.add = lambda self, x, y: x+y
        return cls

class C(object, metaclass=Meta):
    name = 1
    def __init__(self):
        print(12)

    def __new__(cls, *args, **kwargs):
        print(34)
        return object.__new__(cls)


c = C()


class Model(BaseModel):
    name: str

a = Model.construct(**{'name': '123'})
b = Model.construct(**{'name': 1})
print(Model)
print(Model)
print(Model)
print(Model)


class A:
    NAME = 'A'
    def __init__(self):
        A.NAME = 'aaa'

    def __init_subclass__(cls, **kwargs):
        print(cls.NAME)


class B(A):

    def __init__(self):
        print('b')
    NAME = 'B'



class C(A):

    def __init__(self):
        print('c')
    NAME = 'C'


class D(B):
    NAME = 'D'

    def __init__(self):
        print('d')

print(A.NAME)
a = A()
print(a.NAME)
a = A()
print(a.NAME)
b = B()
c = C()
d = D()
print()
print()
print()
print()