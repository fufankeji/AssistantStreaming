import asyncio
from openai import AsyncOpenAI


async def main(asybc_client: AsyncOpenAI):
    response = await asybc_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": "你好，请你介绍一下你自己"
            }
        ]
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    client = AsyncOpenAI()
    # 以前是这样做的，但是acreate被删除了，
    # response = await openai.ChatCompletion.acreate

    # 现在的用法是：OpenAI 提供了 AsyncOpenAI 类进行异步调用

    asyncio.run(main(asybc_client=client))
