import json
import uuid
import chardet
import requests
from utils.auth_util import gen_sign_headers
import time
import datetime
from config.config import APP_ID, APP_KEY, URI, DOMAIN, config
import traceback
import socket
import utils.BizLogger as BizLogger

current_time = datetime.datetime.now()
time_string = current_time.strftime("%Y-%m-%d %H:%M")

errors = ["timeout", "An error occurred.", "429 Too Many Requests", "http://nginx.org/r/error_log ",
          "hit model rate limit", "当前网络出现问题", "qps request limit", "hit model rate limit", "unknown error",
          "network error", "context_length_exceeded", "InternalServerError"]


# def vivo_GPT(prompt, model, sessionId, history=[], verbose=False):
#
#     METHOD = 'POST'
#     params = {
#         'requestId': str(uuid.uuid4())
#     }
#     data = {
#         'prompt': prompt,
#         # "messages": history,
#         'task_type': 'chatgpt',
#         "model": config["model"][model]["name"],
#         "provider": config["model"][model]["provider"],
#         'sessionId': sessionId,
#     }
#     if "params" in config["model"][model].keys():
#         param = config["model"][model]["params"]
#         data["extra"] = param
#     # 使用 verbose 开关控制打印行为
#     if verbose:
#         # 为了保持终端清爽，即使在详细模式下也只打印部分Prompt
#         truncated_prompt = prompt[:200] + '...' if len(prompt) > 200 else prompt
#         print(f"\n--- Calling Model: {model} ---")
#         print(f"Prompt (truncated): {truncated_prompt}")
#     #     print(f"Request Body: {json.dumps(data, ensure_ascii=False)}") # 如需完整请求体，可取消此行注释
#     else:
#         # 在非详细模式下，可以完全不打印，或只打印一个点来表示正在工作
#         # print('.', end='', flush=True) # 取消注释则每次调用打印一个点
#         pass
#     headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
#     url = 'http://{}{}'.format(DOMAIN, URI)
#     # 配置化domain
#     # if "domain" in config["model"][model].keys():
#     #     domain = config["model"][model]["domain"]
#     #     url = 'http://{}{}'.format(domain, URI)
#     time.sleep(5)
#     print(json.dumps(data, ensure_ascii=False))
#     # BizLogger.log_info("vivo_model 请求参数:{}".format(json.dumps(data, ensure_ascii=False)))
#     content = ""
#     try:
#         # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         # s.connect((url, "8080"))
#         response = requests.post(url, json=data, headers=headers, params=params, timeout=600)
#         if response.status_code == 200:
#             res = response.json()
#         else:
#             res = response.text
#         i = 1
#         while any(err in str(res) for err in errors) and i < 3:
#             print(f"检测到错误或限流，正在进行第 {i} 次重试...")
#             time.sleep(5)  # 在重试前等待
#             response = requests.post(url, json=data, headers=headers, params=params, timeout=600)
#             if response.status_code == 200:
#                 res = response.json()
#             else:
#                 res = response.text
#             i += 1
#         # print(res)
#         BizLogger.log_info("vivo_model 请求结果:{}".format(res))
#         if "data" not in res:
#             content = res
#         else:
#             con = res["data"]
#             if con is None:
#                 content = res["data"]
#             else:
#                 if "content" in con.keys() and con["content"]:
#                     content = con["content"]
#                 else:
#                     content = res["msg"]
#         print(content)
#     except:
#         print(traceback.print_exc())
#     # finally:
#     #     s.close()
#     return content
#

def vivo_GPT(prompt, model, sessionId, history=[], verbose=False, show_prompts=False):
    METHOD = 'POST'
    params = {
        'requestId': str(uuid.uuid4())
    }
    data = {
        'prompt': prompt,
        # "messages": history,
        'task_type': 'chatgpt',
        "model": config["model"][model]["name"],
        "provider": config["model"][model]["provider"],
        'sessionId': sessionId,
    }
    # (小优化：'in a_dict' 比 'in a_dict.keys()' 更高效且Pythonic)
    if "params" in config["model"][model]:
        param = config["model"][model]["params"]
        data["extra"] = param

    if verbose:
        truncated_prompt = prompt[:200] + '...' if len(prompt) > 200 else prompt
        print(f"\n--- Calling Model: {model} ---")
        print(f"Prompt (truncated): {truncated_prompt}")
    else:
        pass

    # 控制prompt输出的显示
    if show_prompts:
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(f"调用模型: {model} (sessionId: {sessionId[:8]}...)")


    headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)

    # --- 核心修改开始：动态确定 Domain ---
    # 1. 首先，使用全局默认的 DOMAIN
    request_domain = DOMAIN

    # 2. 检查当前模型配置中是否有自己的 'domain' 键
    if "domain" in config["model"][model]:
        # 3. 如果有，就用模型自己的 domain 覆盖掉默认值
        request_domain = config["model"][model]["domain"]

    # 4. 使用最终确定的 request_domain 来构建 URL
    url = f'http://{request_domain}{URI}'  # 使用 f-string，更现代易读
    # --- 核心修改结束 ---

    time.sleep(5)
    # BizLogger.log_info("vivo_model 请求参数:{}".format(json.dumps(data, ensure_ascii=False)))

    content = ""
    try:
        response = requests.post(url, json=data, headers=headers, params=params, timeout=1200)

        # --- 您原有的响应处理和重试逻辑（保持不变）---
        if response.status_code == 200:
            res = response.json()
        else:
            res = response.text
        i = 1
        while any(err in str(res) for err in errors) and i < 3:
            print(f"检测到错误或限流，正在进行第 {i} 次重试...")
            time.sleep(5)
            response = requests.post(url, json=data, headers=headers, params=params, timeout=1200)
            if response.status_code == 200:
                res = response.json()
            else:
                res = response.text
            i += 1

        BizLogger.log_info("vivo_model 请求结果:{}".format(res))

        if "data" not in res:
            content = res
        else:
            con = res["data"]
            if con is None:
                content = res["data"]
            else:
                # (小优化：使用 .get() 方法，更安全，避免因 'content' 键不存在而报错)
                if con.get("content"):
                    content = con["content"]
                else:
                    content = res.get("msg", str(res))  # 如果 msg 也没有，就返回整个响应字符串

        # 控制响应输出的显示
        if show_prompts:
            print(content)
        else:
            print(f"响应长度: {len(content)} 字符")
            if len(content) < 100:
                print(f"响应内容: {content}")
            else:
                print(f"响应内容: {content[:50]}...{content[-50:] if len(content) > 100 else ''}")
    except:
        print(traceback.print_exc())

    return content


def streaming_vivo_GPT(prompt, model, sessionId, show_prompts=False):
    METHOD = 'POST'
    params = {
        'requestId': str(uuid.uuid4())
    }
    data = {
        'prompt': prompt,
        'task_type': 'chatgpt',
        "model": config["model"][model]["name"],
        "provider": config["model"][model]["provider"],
        'sessionId': sessionId,
    }
    if "params" in config["model"][model].keys():
        param = config["model"][model]["params"]
        data["extra"] = param
    print(f"modelname：{model}")
    global URI
    __URI = URI + "/stream"
    headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, __URI, params)
    url = 'http://{}{}'.format(DOMAIN, __URI)
    time.sleep(0.5)
    # 控制prompt输出的显示
    if show_prompts:
        print(json.dumps(data, ensure_ascii=False))
    BizLogger.log_info("vivo_model 请求参数:{}".format(json.dumps(data, ensure_ascii=False)))
    content = ""
    try:
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # s.connect((url, "8080"))
        print("data:", data)
        print("headers:", headers)
        response = requests.post(url, json=data, headers=headers, params=params, timeout=600, stream=True)
        if response.status_code == 200:
            first_line = True
            for line in response.iter_lines():
                if line:
                    if first_line:
                        encoding = 'utf-8'
                        first_line = False
                    else:
                        encoding = chardet.detect(line)['encoding']
                    line = line.decode(encoding, errors='ignore')
                    print(line)
                    if not "event:close" in line or not 'data:[DONE]' in line:
                        line = line.split("data:")[1]
                        yield json.loads(line)
        else:
            res = response.text
            print(res)

    except:
        print(traceback.print_exc())


def local_GPT(prompt, url="http://10.222.8.126:31272/api/generation_sync "):
    data = {
        'prompt': prompt,
        'parameters': {
            'temperature': 0.95,
            'top_p': 0.8,
            'top_k': 50,
            'max_new_tokens': 2000,
            'repetition_penalty': 1.0,
            'num_beams': 1
        }
    }
    # print(data)
    response = requests.post(url, json=data, timeout=600)
    if response.status_code == 200:
        res = response.json()
    else:
        res = response.text
    # print(res)
    if "result" in res:
        content = res["result"]
    return content


def vivo_GPT_Token(prompt, model, sessionId, show_prompts=False):
    METHOD = 'POST'
    params = {
        'requestId': str(uuid.uuid4())
    }
    data = {
        'prompt': prompt,
        'task_type': 'chatgpt',
        "model": config["model"][model]["name"],
        "provider": config["model"][model]["provider"],
        'sessionId': sessionId,
    }
    if "params" in config["model"][model].keys():
        param = config["model"][model]["params"]
        data["extra"] = param
    print(f"modelname：{model}")
    headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
    url = 'http://{}{}'.format(DOMAIN, URI)
    time.sleep(5)
    # 控制prompt输出的显示
    if show_prompts:
        print(json.dumps(data, ensure_ascii=False))
    BizLogger.log_info("vivo_model 请求参数:{}".format(json.dumps(data, ensure_ascii=False)))
    content = ""
    try:
        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # s.connect((url, "8080"))
        response = requests.post(url, json=data, headers=headers, params=params, timeout=600)
        if response.status_code == 200:
            res = response.json()
        else:
            res = response.text
        i = 1
        while any(item in res for item in errors) and i < 3:
            print("进入重试")
            response = requests.post(url, json=data, headers=headers, params=params, timeout=600)
            if response.status_code == 200:
                res = response.json()
            else:
                res = response.text
            i = i + 1
        print(res)
        BizLogger.log_info("vivo_model 请求结果:{}".format(res))
        result = {}
        if "data" not in res:
            content = res
        else:
            con = res["data"]
            if con is None:
                content = res["data"]
            else:
                if "content" in con.keys() and con["content"]:
                    content = con["content"]
                    result['promptToken'] = con['usage']['promptTokens']
                    result['completionToken'] = con['usage']['completionTokens']
                    result['totalToken'] = con['usage']['totalTokens']
                else:
                    content = res["msg"]
        print(content)
        result['result'] = content
        print(json.dumps(result, ensure_ascii=False))
    except:
        print(traceback.print_exc())
    # finally:
    #     s.close()
    return result


##130B模型请求方式
def get130BResult(messages):
    URL = "http://10.222.8.104:31579/generate "
    params = {
        ##messages格式[{"role":"user","content":""},{"role":"assistant","content":""}]
        "messages": messages,
        "model_name": "glm",
    }
    headers = {"content-type": "application/json"}
    response = requests.post(URL, data=json.dumps(params), headers=headers)
    print(response.text)
    if response.status_code == 200:
        data = response.json()
        text = data["text"]
    else:
        data = response.text
        text = data
    return text


if __name__ == '__main__':
    #     # vivo_GPT("中国共产党领导人是谁", "chatgpt", str(uuid.uuid4()))
    #     i = 1
    #     if i == 1:
    #         res = "{'message':'network error'}"
    #     while any(item in res for item in errors) and i < 3:
    #         print("进入重试")
    #         i = i + 1
    #     shit = streaming_vivo_GPT("你是?", "chatgpt", str(uuid.uuid4()))
    #     for _ in shit:
    #         print(_)
    # multi_turn = ["刘德华有老婆吗？", "毛泽东呢？", "嬴政呢"]
    # system_prompt = "你的回答需要尽可能详细。"
    # history = ""
    # for i, q in enumerate(multi_turn):
    #     q = system_prompt + "\n" + q if i == 0 else q
    #     history = history + "[|Human|]:{}[|AI|]:".format(q)
    #     ans = local_GPT(history)
    #     history = history + ans + "</s>"
    #     print(history)
    # history = ""
    # system_prompt = ""
    # for q in multi_turn:
    #     q = system_prompt + "\n" + q if i == 0 else q
    #     history = history + "[|Human|]:{}[|AI|]:".format(q)
    #     ans = local_GPT(history)
    #     history = history + ans + "</s>"
    #     print(history)
    sessionId = str(uuid.uuid4())
    messages = [{"role":"user","content":"你是谁？"},{"role":"assistant","content":"我是AI助手，是一种人工智能技术应用，可以协助完成各种任务，包括回答问题、提供建议、执行指令等。"},{"role":"user","content":"你会做什么？"}]
    # res = vivo_GPT("你好，你是谁", "chatGLM3_130B_SFT", sessionId,history=messages)
    res = vivo_GPT("你好,你是谁", "chatGLM3_130B_SFT", sessionId)
    print(res)
    
