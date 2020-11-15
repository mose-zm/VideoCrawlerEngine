import asyncio
import os
import shutil
from datetime import datetime
from functools import wraps
from subprocess import list2cmdline
from typing import List, Callable, Union
from context import debugger as dbg
from .__engine__ import requester, CallableData, Requester
from .utils.ffmpeg import FfmpegStreamHandler
from .model.media import FfmpegDataModel


@requester('convert', weight=0.5)
async def ensure_convert():
    """ 同一转换未经过ffmpeg处理的视频，以达到目标的视频编码方式。

    该方法在以下两种情况下在视频处理方面做出的不同的处理：
    1. download下载的视频未经过ffmpeg编码处理：
        1) 搜索所有download下载的视频文件。
        2) 对所有的download下载的视频文件经过ffmpeg指定编码处理。
        3) 得到经过了ffmpeg编码处理的视频文件。

    2. download下载的视频已经经过了ffmpeg编码处理：
        1) 搜索所有经过ffmpeg处理的视频文件。

    将以上两种情况下经过ffmpeg处理的视频文件按照规则从临时目录移动并重命名到目的存储目录。

    在多视频文件的情况下会在视频文件加上前缀，并且放到以标题为名称的子目录下。
    """

    # 如果已经过了ffmpeg处理，经跳过该转换流程
    merges = dbg.glb.task.find_by_name('ffmpeg')

    results = [merge.get_data('filepath') for merge in merges]
    if not results:
        # 对于没有经过ffmpeg处理的工具，转换所有的音视频文件
        downloads = dbg.glb.task.find_by_name('download')
        for filename in [dl.get_data('filepath') for dl in downloads]:
            converter = ffmpeg.convert(filename)
            await converter.end_request()
            results.append(converter.get_data('filepath'))

    # 修改文件名并移动文件
    savedir = os.path.realpath(dbg.glb.config['savedir'])
    # 当文件多于一个的时候在存储目录添加一级目录
    n = dbg.glb.script['n']
    if n > 1:
        savedir = os.path.join(os.path.realpath(savedir), dbg.glb.script['title'])
        if not os.path.isdir(savedir):
            os.makedirs(savedir)

    for filepath in results:
        name = os.path.basename(filepath)
        name = name.split('.', 1)[-1]
        if n > 1:
            name = f'{dbg.b :03}.{name}'
        dst_pathname = os.path.join(savedir, name)
        shutil.move(filepath, dst_pathname)


@requester('ffmpeg', info_model=FfmpegDataModel)
async def ffmpeg(
    inputs: Union[List[str], str],
    gen_cmd: str,
    cal_len,
    **kwargs
):
    """ ffmpeg 数据流处理引擎。"""

    def input2pathname(input):
        if isinstance(input, str):
            return input
        elif isinstance(input, Requester):
            return input.get_data('filepath')
        assert input

    def percent():
        nonlocal time_length, f
        return f.complete_length() * 100 / (time_length or float('inf'))

    time_length = dbg.glb.script['length'] or float('inf')
    temp = dbg.tempdir.mktemp(dbg.glb.config['to_format'])

    inputs = inputs
    if not isinstance(inputs, (list, tuple, set)):
        inputs = [inputs]

    cmd = await getattr(ffmpeg, gen_cmd).__wrapped__(
        inputs=[input2pathname(input) for input in inputs],
        output=temp.filepath,
        **kwargs
    )

    if cal_len and time_length in (float('inf'), None):
        # 总长度计算
        time_length = await cal_total_length(inputs)
        dbg.upload(length=time_length)
    source = os.path.join(dbg.config['source'], dbg.config['name'])

    if isinstance(cmd, (list, tuple)):
        cmd = [source] + list(cmd)
        cmd = list2cmdline(cmd)
    else:
        cmd = f'{source} ' + cmd

    if dbg.config['overwrite']:
        cmd += ' -y'
    print(cmd)

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    f = FfmpegStreamHandler(process)
    dbg.set_speed(f.speed)
    dbg.set_percent(percent)

    dbg.upload(
        cmd=cmd,
        filepath=temp.filepath,
        input=CallableData(f.get_inputs),
        output=CallableData(f.get_outputs),
    )
    dbg.add_stopper(f.stop_threadsafe)
    await f.run(timeout=dbg.config.get('timeout', None), close_stdin=False)
    print('ffmpeg 运行结束！！！！')


def ffmpeg_operator(func=None, *, cal_len=True):
    if func is None:
        def wrapper(func):
            return ffmpeg_operator(func, cal_len=cal_len)
    else:
        @wraps(func)
        def wrapper(inputs, **kwargs):
            return ffmpeg(inputs, gen_cmd=func.__name__, cal_len=cal_len, **kwargs)

        setattr(ffmpeg, func.__name__, wrapper)
    return wrapper


@ffmpeg_operator
async def cmdline(inputs: List, output: str, cmd: str, input_getter=None):
    if input_getter is None:
        return cmd.format(*inputs, output=output)
    else:
        return cmd.format(inputs=input_getter(inputs), output=output)


@ffmpeg_operator
async def concat_av(inputs: List, output: str):
    video, audio = inputs
    cmd = ['-i', f'{video}',
           '-i', f'{audio}',
           '-vcodec', 'copy', '-acodec', 'copy',
           f'{output}']
    return cmd


@ffmpeg_operator
async def concat_demuxer(inputs: List, output: str):
    tempfile = dbg.tempdir.mktemp('.txt')
    concat_input = '\n'.join([f'file \'{input}\'' for input in inputs])

    with tempfile.open('w') as f:
        f.write(concat_input)

    cmd = ['-f', 'concat', '-safe', '0',
           '-i', f'{tempfile.filepath}', '-c', 'copy', f'{output}']
    return cmd


@ffmpeg_operator
async def concat_protocol(inputs: List, output: str):
    concat_input = '|'.join(inputs)
    cmd = ['-i', f'concat:\'{concat_input}\'', '-c', 'copy', f'{output}']
    return cmd


@ffmpeg_operator(cal_len=False)
async def information(inputs: List, **options):
    cmd = []
    for input in inputs:
        cmd.extend(['-i', input])

    return cmd


@ffmpeg_operator
async def concat_m3u8(inputs, output, **options):
    cmd = await concat_demuxer(inputs, output).end_request()
    return cmd


@ffmpeg_operator(cal_len=False)
async def m3u8download(
    inputs: List,
    output: str,
    user_agent: str = ('Mozilla/5.0 (Windows NT 6.1; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36'),
    headers: dict = None,
    **options
):
    """ m3u8文件下载。"""
    headers = headers or {}
    cmd = ['-user_agent', f'"{user_agent}"']
    # 设置参数
    headers_params = []
    for k, v in headers.items():
        if v is True:
            v = ''

        headers_params.extend([f'-{k}', v])
    if headers_params:
        cmd.append('-headers')
        cmd.extend(headers_params)

    # 设置输入链接
    for input in inputs:
        cmd.extend(['-i', f'"{input}"'])

    # 设置输出路径
    cmd += ['-c', 'copy', output]
    cmd = ' '.join(cmd)
    return cmd


async def cal_total_length(inputs, **options):
    """ 视频长度批量计算。"""
    info = information(inputs)
    await info.end_request()
    all_inputs = info.get_data('input', {})
    length = 0
    for input in all_inputs:
        for stream in input.get('streams', []):
            for s in stream['streams']:
                if s['type'] == 'video':
                    has_video = True
                    break
            else:
                has_video = False

            # 仅在stream有video的时候时间才进行累加计算。
            if has_video:
                duration = datetime.strptime(stream['duration'], '%H:%M:%S.%f')
                length += (
                    duration.hour * 3600 +
                    duration.minute * 60 +
                    duration.second +
                    duration.microsecond * 1e-6
                )
    return length


@ffmpeg_operator
async def convert(inputs, output, h265=False):
    input, *_ = inputs
    cmd = ['-i', input, '-y', '-qscale', '0', '-vcodec', 'libx264', output]
    return cmd