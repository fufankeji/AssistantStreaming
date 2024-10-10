import logging
import asyncio
from openai import AsyncOpenAI, OpenAI
from server.assistant import OpenAIAssistant
from server.utils import create_assistant, create_thread, delete_thread, chat_with_assistant


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # 初始化异步的客户端
    client = AsyncOpenAI()
    # 初始化同步的客户端
    sync_client = OpenAI()

    # 初始化 Assistant 类实例
    assistant_instance = OpenAIAssistant(client=client)
    # 创建 assistant 对象实例
    assistant = await create_assistant(assistant_instance)
    # 创建 thread 实例
    thread = await create_thread(client=client)

    while True:
        try:
            query = input("请输入你的问题. (输入 '退出' 结束当前对话)：")
            if query.lower().strip() == "退出":
                break

            # 实现对话的主函数
            async for token in chat_with_assistant(assistant=assistant, thread=thread, user_query=query, client=client):
                print(token, end='')

        except Exception:
            logger.exception("error in chat: ")

    # 删除线程
    delete_thread(thread_id=thread.id, sync_client=sync_client)


if __name__ == '__main__':
    asyncio.run(main())
