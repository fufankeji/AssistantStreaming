from openai import AsyncOpenAI, OpenAI
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAIAssistant:
    def __init__(self, client):
        self.client = client
        self.assistant_id = None

    async def get_or_create_assistant(self, name, model):
        try:
            # 尝试获取现有assistant对象
            self.assistant = await self.client.beta.assistants.retrieve(name=name)
            self.assistant_id = self.assistant.id
            # return self用来返回当前类的实例（即对象本身）。这样做通常用于链式调用，即允许多个方法可以连续调用。
            return self
        except Exception:
            self.assistant = await self.client.beta.assistants.create(
                name=name,
                model=model,
                instructions="You are a helpful AI assistant who is adept at using tools to answer questions posed by users",
            )
            self.assistant_id = self.assistant.id
            return self

    async def set_description_and_instructions(self, instructions):
        # 更新助理的指令
        self.assistant = await self.client.beta.assistants.update(
            assistant_id=self.assistant_id,
            instructions=instructions
        )
        return self

    async def set_tools(self, tools):
        # 检查 tools 列表中是否包含 {"type": "file_search"}
        contains_file_search = any(tool['type'] == 'file_search' for tool in tools)

        with open('vector_store_id.txt', 'r') as file:
            vector_store_id = file.read().strip()
        logger.info(f"written vector_store_id：{vector_store_id}")
        # 根据条件添加 tool_resources
        if contains_file_search:
            # 如果存在 {"type": "file_search"}，添加 tool_resources 参数
            await self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                tools=tools,
                tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
            )
        else:
            # 如果不存在，只更新 tools 参数
            await self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                tools=tools
            )

        return self


if __name__ == '__main__':
    client = AsyncOpenAI()
    sync_client = OpenAI()
    assistant_instance = OpenAIAssistant(client=client)
    print(assistant_instance)
