from typing import Type, get_origin, get_args, Union, Any
from types import NoneType
from tools.base_tool import BaseTool


def infer_field_type(field_type: Any) -> str:
    """
    根据给定的 Python 类型确定 JSON schema 类型，特别是处理 Optional 类型。

    :param field_type: 要从中推断的 Python 类型。
    :return: 表示 JSON schema 类型的字符串。
    """
    if get_origin(field_type) is Union:
        # 提取实际类型，如果字段是 Optional（与 NoneType 的联合）
        non_none_types = [t for t in get_args(field_type) if t is not type(None)]
        return infer_field_type(non_none_types[0]) if non_none_types else 'null'

    # Python 类型到 JSON schema 类型的映射
    type_mappings = {
        str: 'string',
        int: 'integer',
        float: 'float',
        bool: 'boolean'
        # 根据需要添加更多映射
    }

    return type_mappings.get(field_type, 'string')  # 如果类型未识别，默认为 'string'


def generate_openai_function_spec(tool_class: Type[BaseTool]) -> dict:
    """
    根据给定的工具类生成符合 OpenAI API 函数调用格式的规格说明。

    :param tool_class: 要生成函数规格说明的类。
    :return: 格式化为 OpenAI API 函数规格的字典。
    """
    function_name = tool_class.get_name()
    description = tool_class.get_description()
    args_schema = tool_class.get_args_schema()

    properties = {}
    required_fields = []

    # 遍历工具类中定义的 Pydantic 模型字段， args_schema.__annotations__.items() 是一种访问类或函数的类型注解的方法
    for field_name, field_model in args_schema.__annotations__.items():
        field_info = args_schema.__fields__[field_name]
        field_description = field_info.description or ''
        field_type = infer_field_type(field_model)

        properties[field_name] = {"type": field_type, "description": field_description}

        # 处理枚举类型，如果字段模型是枚举类型
        if hasattr(field_model, '__members__'):
            properties[field_name]['enum'] = [e.value for e in field_model]

        # 从必填字段中排除 Optional 字段：检查字段类型是否包含 NoneType，以判断是否是 Optional
        if get_origin(field_model) is Union:
            type_args = get_args(field_model)
            if NoneType not in type_args:
                required_fields.append(field_name)
        else:
            required_fields.append(field_name)

    function_spec = {
        "type": "function",
        "function": {
            "name": function_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_fields
            }
        }
    }

    return function_spec

if __name__ == '__main__':
    from tools.python_inter import PythonInterpreterTool
    function_spec = generate_openai_function_spec(PythonInterpreterTool)
    print(function_spec)