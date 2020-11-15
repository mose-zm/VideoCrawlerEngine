# -*- coding: utf-8 -*-

from requester.__engine__ import REQ_STOPPED, REQ_DONE, REQ_ERROR, REQ_READY, REQ_RUNNING
from script import select_script
from requester.builtin import start_task, FakeTask
from contexts import a, b, abcdef
from collections import defaultdict
from functools import _make_key as make_key, _HashedSeq as HashedSeq
from script import supported_script
import hashlib
from contexts import glb
from context import debugger as dbg

from utils.common import cat_a4f

__task_stacks__ = {}


class TaskStack:
    def __init__(self, url, **options):
        self.url = url
        self.options = options
        if dbg.__debug_mode__:
            task = FakeTask(**options)
        else:
            task = start_task(url, **options)
        self.taskreq = task
        self.running = set()
        self.all_branches_works = defaultdict(dict)

    @property
    def key(self):
        return gen_task_key(self.url, **self.options)

    @property
    def blen(self):
        return len(self.all_branches_works)

    @property
    def current_branch(self):
        return self.all_branches_works[f'{a()}-{b()}']

    def all_works(self):
        for k, v in self.all_branches_works.items():
            yield from v.items()

    def run_background(self):
        with a.enter(0), glb['task'].enter(self):
            return self.taskreq.start_request()

    def debug(self, o, **options):
        assert dbg.__debug_mode__
        with glb['task'].enter(self):
            self.taskreq.start_request()
            self.taskreq.run(o, **options)

    def stop(self):
        self.taskreq.stop()

    def __enter__(self):
        print(abcdef.get())
        self.running.add(abcdef.get())

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running.remove(abcdef.get())

    def add_work(self, work):
        self.current_branch[work.__locale__] = work

    def find_by_name(self, name):
        """ 寻找节点。"""
        return [v for k, v in self.current_branch.items() if v.NAME == name]

    def detail(self):
        all_nodes = {}
        requesters = defaultdict(list)
        sum_weight = 0
        all_works = dict(self.all_works())
        # details = {}
        for k, v in all_works.items():
            # all_nodes[cat_a4f(k)] = RequestStateModel(
            #     id=cat_a4f(k),
            #     type=v.TYPE,
            #     name=v.NAME,
            #     percent=round(v.progress.percent, 3),
            #     status=v.progress.status,
            #     log=(len(v.progress.logs) and v.progress.logs[-1]) or '',
            #     err=''
            # )
            all_nodes[cat_a4f(k)] = {
                'id': cat_a4f(k),
                'type': v.TYPE,
                'name': v.NAME,
                'percent': round(v.progress.percent, 3),
                'status': v.progress.status,
                'log': (len(v.progress.logs) and v.progress.logs[-1]) or '',
                'errMsg': '',
                'body': []
            }
            if v.NAME not in requesters:
                sum_weight += v.WEIGHT
            requesters[v.NAME].append(v)
            # details[cat_abcde(k)] = self.detail(cat_abcde(k))

        # 节点进度权重计算
        sum_percent = 0
        req_ratios = []

        error_flag = False
        stopped_flag = False
        for k, v in requesters.items():
            # 请求器完成百分比
            req_percent = sum([i.progress.percent for i in v])
            weight = v[0].WEIGHT
            percent = (req_percent / len(v)) * (weight / sum_weight)
            # 运行状态
            is_stopped = any([i.progress.status == REQ_STOPPED for i in v])
            is_error = any([i.progress.status == REQ_ERROR for i in v])
            status = REQ_READY
            if is_stopped:
                status = REQ_STOPPED
                stopped_flag = True
            elif is_error:
                status = REQ_ERROR
                error_flag = True
            elif req_percent / len(v) == 100:
                status = REQ_DONE
            elif req_percent > 0:
                status = REQ_RUNNING

            # req_ratios.append(RequestRadioModel(
            #     name=k,
            #     weight=weight,
            #     percent=round(percent, 3),
            #     status=status
            # ))

            req_ratios.append({
                'name': k,
                'weight': weight,
                'percent': round(percent, 3),
                'status': status,
            })
            sum_percent += percent

        if sum_percent == 100:
            status = REQ_DONE
        elif error_flag:
            status = REQ_ERROR
        elif stopped_flag:
            status = REQ_STOPPED
        elif sum_percent > 0:
            status = REQ_RUNNING
        elif sum_percent == 0:
            status = REQ_READY
        else:
            status = 'unknown'

        # return TaskStateModel(
        #     title=self.taskreq.get_data('title') or self.key,
        #     n=len(all_works),
        #     running=[cat_a4f(i) for i in self.running],
        #     ratios=req_ratios,
        #     percent=round(sum_percent, 3),
        #     url=self.url,
        #     status=status
        # )

        return {
            'title': self.taskreq.get_data('title') or self.key,
            'n': len(all_works),
            'runningNodes': [cat_a4f(i) for i in self.running],
            'allNodes': all_nodes,
            'requesterRatio': req_ratios,
            'percent': round(sum_percent, 3),
            'url': self.taskreq.get_data('url'),
            'status': status,
            # 'details': details
        }

    def node_detail(self, abcde_str):
        a, b, c, d, e = abcde_str.split('-')
        abcde_tuple = (int(a), int(b), int(c), int(d), int(e))
        request = self.all_branches_works[f'{a}-{b}'][abcde_tuple]
        data = dict(request.progress.iter_data())
        return data

    @classmethod
    def new(cls, url, **options):
        global __task_stacks__
        key = gen_task_key(url, **options)
        if key in __task_stacks__:
            raise FileExistsError()
        task = cls(url, **options)
        __task_stacks__[key] = task

        sel_script = select_script(cls.get_supported(url))
        task.run_background()
        return {
            'script': sel_script,
            'key': key,
            'url': url,
        }

    @staticmethod
    def get_supported(url):
        return supported_script(url)

    @staticmethod
    def simple_all():
        global __task_stacks__
        return {
            k: v.detail() for k, v in __task_stacks__.items()
        }

    @staticmethod
    def get_task(key):
        global __task_stacks__
        return __task_stacks__[key]


def gen_task_key(*args, **kwargs):
    key = make_key(args, kwargs, False)
    if isinstance(key, HashedSeq):
        key = key.hashvalue
    else:
        key = hash(key)
    return hashlib.md5(
        hex(key).encode('utf-8')
    ).hexdigest()


if __name__ == '__main__':
    class TestNode:
        def __init__(self, name):
            print(name)
