from openai.types.beta import Assistant, Thread
from openai.types.beta.threads import Run, RequiredActionFunctionToolCall
from openai.types.beta.assistant_stream_event import (
    ThreadRunRequiresAction, ThreadMessageDelta, ThreadRunCompleted,
    ThreadRunFailed, ThreadRunCancelling, ThreadRunCancelled, ThreadRunExpired, ThreadRunStepFailed,
    ThreadRunStepCancelled)
from server.run import AsyncChain
from tools.python_inter import PythonInterpreterTool
from tools.utils import generate_openai_function_spec

import logging

import asyncio
import json
from typing import Dict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tool_instances = {}


async def create_assistant(assistant_instant) -> Assistant:
    global tool_instances

    assistant_name = "Data Engineer"
    assistant_model = "gpt-4o"
    assistant_instructions = "You're a senior data analyst. When asked for data information, write and run Python code to answer the question"

    # 构造一个链路，用于管理同一个对象上异步的链式调用方法
    chain = AsyncChain(assistant_instant)

    # 这里定义内置的工具，file_search 或者 code interpreter
    default_tools = [
        {"type": "file_search"}
    ]

    # 这里定义自定义工具
    tools = [PythonInterpreterTool]

    tool_instances = {tool_cls.get_name(): tool_cls(logger=logger) for tool_cls in tools}

    tools_spec = [generate_openai_function_spec(tool_cls) for tool_cls in tools]

    default_tools.extend(tools_spec)

    # 执行异步链顺序调用
    openai_assistant_instance = await (
        chain.get_or_create_assistant(name=assistant_name, model=assistant_model)
        .set_description_and_instructions(instructions=assistant_instructions)
        .set_tools(default_tools)
        .execute()
    )

    openai_assistant = openai_assistant_instance.assistant
    logger.info(f"created assistant {openai_assistant.name} with id: {openai_assistant.id}")
    return openai_assistant


async def create_thread(client) -> Thread:
    thread = await client.beta.threads.create()
    logger.info(f"created new thread: {thread.id}")
    return thread


def delete_thread(thread_id, sync_client):
    thread_deleted = sync_client.beta.threads.delete(thread_id=thread_id)
    logger.info(f"deleted thread {thread_id}: {thread_deleted.deleted}")


async def kill_if_thread_is_running(thread_id: str, client):
    runs = client.beta.threads.runs.list(
        thread_id=thread_id
    )

    running_threads = []
    async for run in runs:
        if run.status in ["in_progress", "queued", "requires_action", "cancelling"]:
            running_threads.append(run)

    async def kill_run(run_to_kill: Run):
        counter = 0
        try:
            while True:
                run_obj = await client.beta.threads.runs.retrieve(run_id=run_to_kill.id, thread_id=thread_id)
                run_status = run_obj.status
                if run_status == "cancelling":
                    logger.info(f"run {run_to_kill.id} is being cancelled, waiting for it to get cancelled")
                    await asyncio.sleep(2)
                    continue

                if run_status in ["cancelled", "failed", "completed", "expired"]:
                    logger.info(f"run {run_to_kill.id} is cancelled")
                    break

                run_obj = await client.beta.threads.runs.cancel(
                    thread_id=thread_id,
                    run_id=run_to_kill.id
                )

                if run_obj.status in ["cancelled", "failed", "expired"]:
                    logger.info(
                        f"run {run_obj.id} for thread {thread_id} is killed. status is {run_obj.status}")
                    break

                else:
                    logger.info(
                        f"run {run_obj.id} for thread {thread_id} is not yet killed. status is {run_obj.status}")
                    counter += 1
                    await asyncio.sleep(2)
                    continue

        except Exception:
            logger.exception(f"error in killing thread: {thread_id}")
            raise Exception(f"error in killing thread: {thread_id}")

    if not running_threads:
        logger.info(f"no running threads for thread : {thread_id}")
        return

    if running_threads:
        logger.info(f"total {len(running_threads)} running threads")
        tasks = []
        for run_obj in running_threads:
            # 需要并发运行多个异步操作时，使用create_task
            task = asyncio.create_task(kill_run(run_obj))
            await asyncio.sleep(0)
            tasks.append(task)

        # done包含那些在 asyncio.wait() 调用完成时已经完成的任务。无论是正常完成还是因为异常而结束的任务都会包含在这个集合中。
        # pending 包含那些在 asyncio.wait() 调用完成时仍然未完成的任务。这些任务可能是因为超时或者仍在等待某些操作的完成。
        done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED, timeout=120)
        no_of_exceptions = 0

        for done_task in done:
            if done_task.exception() is None:
                task_result = done_task.result()
                if task_result:
                    logger.info(f"status of run kill task: {done_task} is {task_result}")

            else:
                if logger:
                    logger.exception(f"error in run kill task: {done_task}, "
                                     f"exception: {done_task.exception()}")

                no_of_exceptions += 1

        for pending_task in pending:
            logger.info(f"cancelling run kill task: {pending_task}")
            pending_task.cancel()

        if no_of_exceptions > 0 or pending:
            raise Exception("failed to kill running threads")


async def handle_function_call(tool_call: RequiredActionFunctionToolCall) -> (str, str):
    if tool_call.type != "function":
        return None, None
    tool_id = tool_call.id
    function = tool_call.function
    function_name = function.name
    function_args = json.loads(function.arguments)
    try:
        logger.info(f"calling function {function_name} with args: {function_args}")
        function_result = await tool_instances[function_name].arun(**function_args)
        logger.info(f"got result from {function_name}: {function_result}")
    except Exception as e:
        logger.exception(f"Error handling function call: {e}")
        function_result = None
    return tool_id, function_result


async def handle_function_calls(run_obj: Run) -> Dict[str, str]:
    required_action = run_obj.required_action
    if required_action.type != "submit_tool_outputs":
        return {}

    tool_calls = required_action.submit_tool_outputs.tool_calls
    results = await asyncio.gather(
        *(handle_function_call(tool_call) for tool_call in tool_calls)
    )
    return {tool_id: result for tool_id, result in results if tool_id is not None}


async def submit_tool_outputs(thread_id: str, run_id: str, function_ids_to_result_map: Dict[str, str], client,
                              stream=False):
    tool_outputs = [{"tool_call_id": tool_id, "output": result if result is not None else ""} for tool_id, result in
                    function_ids_to_result_map.items()]

    logger.info(f"submitting tool outputs: {tool_outputs}")
    run = await client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id,
                                                             run_id=run_id,
                                                             tool_outputs=tool_outputs,
                                                             stream=stream)

    return run


async def process_event(event, thread: Thread, client, **kwargs):
    if isinstance(event, ThreadMessageDelta):
        data = event.data.delta.content
        for text in data:
            yield text.text.value
            # print(text.text.value, end='', flush=True)

    elif isinstance(event, ThreadRunRequiresAction):
        run_obj = event.data
        function_ids_to_result_map = await handle_function_calls(run_obj)
        tool_output_events = await submit_tool_outputs(thread.id,
                                                       run_obj.id,
                                                       function_ids_to_result_map,
                                                       client=client,
                                                       stream=True)
        async for tool_event in tool_output_events:
            async for token in process_event(tool_event, thread=thread, client=client, **kwargs):
                yield token

    elif any(isinstance(event, cls) for cls in [ThreadRunFailed, ThreadRunCancelling, ThreadRunCancelled,
                                                ThreadRunExpired, ThreadRunStepFailed, ThreadRunStepCancelled]):
        raise Exception("Run failed")

    elif isinstance(event, ThreadRunCompleted):
        print("\nRun completed")

    else:
        pass
        # print("\nRun in progress")


async def chat_with_assistant(assistant: Assistant, thread: Thread, user_query: str, client, **kwargs):
    # 需要先清除正在运行的thread
    await kill_if_thread_is_running(thread_id=thread.id, client=client)
    # 创建新一轮的消息到线程中
    message = await client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_query)
    logger.info(f"created message: {message}")

    stream = await client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        stream=True
    )

    async for event in stream:
        async for token in process_event(event, thread, client=client, **kwargs):
            yield token


if __name__ == '__main__':
    from openai import OpenAI

    client = OpenAI()

    # 准备上传文件
    file_paths = [
        "../data/01_LLMs/AI Agent开发入门.pdf",
        "../data/01_LLMs/ChatGLM3-6B零基础部署与使用指南.pdf",
        "../data/01_LLMs/ChatGLM3模型介绍.pdf"
    ]

    # 遍历文件路径并上传文件
    uploaded_files = []
    for path in file_paths:
        with open(path, "rb") as file:
            new_file = client.files.create(
                file=file,
                purpose="assistants"
            )
            uploaded_files.append(new_file.id)

    print(f"uploaded_files:{uploaded_files}")

    vector_store = client.beta.vector_stores.create(
        name="llms",
        file_ids=uploaded_files
    )

    print(f"vector_store:{vector_store.id}")

    # 写入 vector_store.id 到文件
    file_path = "../vector_store_id.txt"  # 可以修改为你项目中具体的路径
    with open(file_path, 'w') as file:
        file.write(vector_store.id)
        print(f"Vector Store ID '{vector_store.id}' has been written to {file_path}")
