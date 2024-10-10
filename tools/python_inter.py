import asyncio
from pydantic import BaseModel
from typing import Type
from tools.base_tool import BaseTool


class PythonInterpreterInput(BaseModel):
    py_code: str  # Python 代码作为字符串


class PythonInterpreterTool(BaseTool):
    name: str = "PythonInterpreterTool"
    description: str = "Executes Python code and returns the result or error message."
    args_schema: Type[BaseModel] = PythonInterpreterInput

    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger

    @staticmethod
    def get_name():
        return "PythonInterpreterTool"

    @staticmethod
    def get_description():
        return "A tool to execute Python code and returns the result or error message."

    @staticmethod
    def get_args_schema():
        return PythonInterpreterInput

    def run(self, py_code: str) -> str:
        try:
            # 尝试如果是表达式，则返回表达式运行结果
            return str(eval(py_code))
        except Exception as e:
            # 如果 eval 失败，则尝试执行 exec
            try:
                exec(py_code)
                return "代码已顺利执行"
            except Exception as exec_error:
                if self.logger:
                    self.logger.error(f"Error while executing code: {exec_error}")
                return f"代码执行时报错: {exec_error}"

    async def arun(self, py_code: str) -> str:
        """
        Asynchronously executes Python code and returns the result or error message.

        :param py_code: The Python code to execute.
        :return: The result of the execution or an error message if an exception occurs.
        """
        loop = asyncio.get_running_loop()
        try:
            # 将 eval 运行在执行器中，以便异步运行
            result = await loop.run_in_executor(None, eval, py_code)
            return str(result)

        except Exception as e:
            # 如果 eval 失败，尝试执行 exec
            try:
                await loop.run_in_executor(None, exec, py_code)
                return "代码已顺利执行"
            except Exception as exec_error:
                if self.logger:
                    self.logger.error(f"Error while executing code: {exec_error}")
                return f"代码执行时报错: {exec_error}"
