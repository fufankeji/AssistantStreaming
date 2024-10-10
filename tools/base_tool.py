from pydantic import BaseModel, Field, Extra
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC, BaseModel):
    # 使用 pydantic 的 Field 类定义字段，并附带描述，增强代码的可读性和文档自动生成的能力。
    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="A description of what the tool does")

    # __init_subclass__ 用于在子类创建时进行检查，确保每个子类都有 'name' 和 'description' 属性。
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'name') or not hasattr(cls, 'description'):
            raise TypeError("Subclasses must define 'name' and 'description'")

    # Config 类提供 pydantic 模型的配置信息。
    class Config:
        """Configuration for this pydantic object."""
        # 允许模型接受额外字段
        extra='allow'
        # 允许模型使用任意类型的字段
        arbitrary_types_allowed = True

    # 以下是抽象方法，定义了所有工具类必须实现的接口。
    @staticmethod
    @abstractmethod
    def get_name() -> str:
        # 必须由子类实现，用于获取工具的名称。
        """Retrieve the name of the tool."""
        raise NotImplementedError("Subclasses must implement 'get_name' method")

    @staticmethod
    @abstractmethod
    def get_description() -> str:
        # 必须由子类实现，用于获取工具的描述。
        """Retrieve a description of the tool."""
        raise NotImplementedError("Subclasses must implement 'get_description' method")

    @staticmethod
    @abstractmethod
    def get_args_schema() -> Any:
        # 必须由子类实现，用于定义工具运行所需的参数结构。
        """Retrieve the argument schema for the tool."""
        raise NotImplementedError("Subclasses must implement 'get_args_schema' method")

    @abstractmethod
    def run(self, *args, **kwargs) -> str:
        # 必须由子类实现，定义工具的同步执行逻辑。
        """Run the tool synchronously."""
        raise NotImplementedError("Subclasses must implement 'run' method")

    async def arun(self, *args, **kwargs) -> str:
        # 必须由子类实现，定义工具的异步执行逻辑。
        """Run the tool asynchronously."""
        raise NotImplementedError("Subclasses must implement 'arun' method if needed")
