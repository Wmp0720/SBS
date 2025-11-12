
import json
import re
from typing import Union

"""
    用来处理大模型输出的各种格式
"""
def clean_json_markdown(raw: str) -> str:
    """
    清理模型输出中的 Markdown 包裹（如 ```json ... ```），返回干净的 JSON 字符串。
    """
    return re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", raw.strip())

def parse_result_json(result: Union[str, dict]) -> dict:
    """
    解析模型返回的 JSON 内容，自动处理 markdown 包裹、嵌套结构等常见异常格式。
    
    参数：
        result: 可以是 str 或 dict 类型的模型输出
    
    返回：
        解析后的 dict 对象（若失败将抛出异常）
    """
    if isinstance(result, dict):
        # 如果已经是合法 JSON 对象
        if all(k in result for k in ["大模型A二级满意度", "竞品二级满意度", "大模型A大模型B对比"]):
            return result
        # 某些平台封装在 content 字段中
        if "data" in result and "content" in result["data"]:
            result_str = result["data"]["content"]
        elif "content" in result:
            result_str = result["content"]
        else:
            raise ValueError("dict 格式中未找到可识别字段")
    elif isinstance(result, str):
        result_str = result
    else:
        raise TypeError("result 必须是 str 或 dict 类型")

    cleaned = clean_json_markdown(result_str)
    return json.loads(cleaned)