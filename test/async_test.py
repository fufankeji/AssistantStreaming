import asyncio


def hello():
    """
    常规函数
    :return:
    """
    return 'hello'


async def hello_async():
    """
    使用async def关键字创建的 async function（异步函数）
    :return:
    """
    return 'hello_async'


async def main():
    x = await hello_async()
    print(x)


async def hello_test():
    print('start')
    await asyncio.sleep(1)
    print('end')


async def multi_main():
    await asyncio.gather(hello_test(), hello_test(), hello_test())


if __name__ == '__main__':
    # 常规函数
    print(hello)  # <function hello at xxxxxxx>

    # 异步函数，当打印它时，仍然可以得到一个函数类型。但是当像调用普通函数一样调用异步函数时，它返回一个协程对象而不是其返回值。
    print(hello_async())  # <coroutine object hello_async at xxxxxx>

    # 协程：一种特殊的函数——当其他任务正在执行时可以暂停和恢复的函数。协程还可以暂时将控制权移交给其他协程。这个机制就允许同时执行多个任务。

    # 正确的运行方式如下：
    # 在另一个协程main中调用hello_async ，需要使用await关键字，但是注意：只能在使用“async def”定义的函数中使用“await”
    # 可以将await hello()视为“等待hello_async()完成，然后将返回值分配给x” ——这就是为什么当打印x时，得到的是hello_async 。
    asyncio.run(main())

    # asyncio.gather()同时运行多个协程
    # 当运行时，首先打印 3 个start, 经过大约 1 秒的延迟后，打印 3 个end。
    # 这是因为：asyncio.sleep(1)使协程休眠 1 秒，asyncio.gather同时运行 3 个hello_test()协程
    asyncio.run(multi_main())
