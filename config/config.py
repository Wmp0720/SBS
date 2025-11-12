import json

import yaml
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

APP_ID = None
APP_KEY = None
URI = None
DOMAIN = None
config = None


def load_config():
    global APP_ID, APP_KEY, URI, DOMAIN, config
    with open(current_dir + "/model.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    APP_ID = str(config["application"]["appid"])
    APP_KEY = config["application"]["appkey"]
    URI = config["application"]["uri"]
    DOMAIN = config["application"]["domain"]


def load_prompt():
    with open(current_dir + "/prompt.yaml", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)
    return prompts


def load_prompt_rule():
    """
    return:所有的prompt、rule、data(字典)，key是度量任务名称
    """
    prompt = {}
    rule = {}
    data = {}
    prompts = load_prompt()
    with open(current_dir + "/config.yaml", encoding="utf-8") as f:
        prompt_rules = yaml.safe_load(f)
        for key, value in prompt_rules.items():
            key_prompt = value.get("prompt", "")
            key_rule = value["rule"]
            if key_rule.endswith(".yaml"):
                with open(current_dir + "/" + key_rule, encoding="utf-8") as f1:
                    rule[key] = yaml.safe_load(f1)
            if key_prompt:
                prompt[key] = prompts[key_prompt]
            data[key] = value["data"]
    return prompt, rule, data


def load_copilot_config():
    copilot_config = {}
    with open(current_dir + "/copilot.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        for key, value in data.items():
            for value_key, value_value in value.items():
                copilot_config[value_key] = str(value_value)
    return copilot_config


def load_copilot_prompt():
    with open(current_dir + "/copilot_prompt.yaml", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)
    return prompts


def load_multi_prompt():
    with open(current_dir + "/multi.yaml", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)
    return prompts


##加载长文本prompt
def load_longctx_prompt():
    with open(current_dir + "/longctx.yaml", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)
    return prompts


load_config()

if __name__ == "__main__":
    prompt, _, __ = load_prompt_rule()
    # prompt = load_longctx_prompt()
    print(json.dumps(prompt, ensure_ascii=False))
    print(json.dumps(_, ensure_ascii=False))
    print(json.dumps(__, ensure_ascii=False))