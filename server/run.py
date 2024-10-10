from types import NoneType
from typing import Type, get_origin, get_args, Union, Any


class AsyncChain:
    """
    AsyncChain 类的目的是允许对一个对象进行一系列的异步操作，并按顺序执行这些操作。
    """

    def __init__(self, obj):
        """
        初始化 AsyncChain，设置目标对象，方法将在此对象上被调用。

        :param obj: 方法将被调用的对象。
        """
        self._obj = obj  # obj 是任何一个 Python 对象
        self._calls = []  # 初始化函数将传入的对象保存在 self._obj 中，并初始化一个空列表 self._calls，用于存储所有待执行的异步方法调用。

    def __getattr__(self, name):
        """
        这个方法是 Python 的魔法方法，它在你尝试访问对象的某个属性（这里是方法）时被调用，但这个属性在对象的常规属性列表中不存在。

        返回一个方法，该方法会将它的异步调用添加到链中。

        :param name: 对象上要调用的方法的名称。
        :return: 一个可调用对象，将异步方法调用添加到链中。
        """

        def method(*args, **kwargs):
            async def async_call():
                # 它从 _obj 中获取真正要调用的方法，并在适当的时候（即 execute 被调用时）执行这个方法。
                func = getattr(self._obj, name)
                self._obj = await func(*args, **kwargs)

            # 通过将 async_call 添加到 _calls 列表，实际上是在排队等待这个调用的执行。
            self._calls.append(async_call)
            return self

        return method

    async def execute(self):
        """
        execute 方法是一个异步方法，它按照 self._calls 列表中的顺序依次执行所有的异步方法调用。

        按添加的顺序执行所有链式的异步方法调用。

        :return: 经过所有链式调用修改后的对象。
        """
        for call in self._calls:
            await call()
        return self._obj