import logging
import json
import random
import config

class workflow:
    prompt_json = None
    def __init__(self,filename):
        self.read_workflow(filename)

    # 读入的文件应该是一个json文件，返回josn对象
    def read_workflow(self,filename):
        logging.info(f"加载workflow...")
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            self.prompt_json = json.loads(content)
        except Exception as e:
            logging.error(f"{e}")

    def searchWorkflowNode(self, class_type_value):
        for nodeNum, nodeParam in self.prompt_json.items():
            for paramKey, paramValue in nodeParam.items():
                if paramKey == "class_type":
                    if paramValue == class_type_value:
                        logging.debug(f"searchMatch nodeNum = {nodeNum}")
                        return nodeNum
        logging.warning(f"跳过,未找到workflow节点:{class_type_value}")

    def set_workflow_prompt_word(self,prompt_word):
        logging.info(f"设置提示词")
        nodeNum = self.searchWorkflowNode("CLIPTextEncode")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["text"] = prompt_word
            logging.debug(f"set prompt = {prompt_word}")

    def set_workflow_param(self):
        logging.info(f"设置参数...")
        logging.info(f"设置KSampler随机seed")
        # 生成 0 到 2^64-1 之间的随机整数（8 字节）
        random_int = random.randrange(0, 2**64)
        nodeNum = self.searchWorkflowNode("KSampler")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["seed"] = random_int
            logging.debug(f"set seed = {random_int}")

class workflow_wan(workflow):
    def set_workflow_prompt_word(self,prompt_word):
        logging.info(f"设置提示词...")
        
        nodeNum = self.searchWorkflowNode("WanVideoTextEncode")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["positive_prompt"] = prompt_word
            logging.debug(f"set prompt = {prompt_word}")

    def set_workflow_source_image(self,imagePatch):
        logging.info(f"设置图片源...")
        nodeNum = self.searchWorkflowNode("LoadImage")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["image"] = imagePatch
            logging.debug(f"use image = {imagePatch}")

    def set_workflow_param(self):
        logging.info(f"设置参数...")
        """
        nodeNum = self.searchWorkflowNode("WanVideoSampler")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["steps"] = 1
            logging.debug(f"set steps = {1}")"
        """

        nodeNum = self.searchWorkflowNode("VHS_VideoCombine")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["filename_prefix"] = config.wan_output_file_name
            logging.debug(f"set output file name = {config.wan_output_file_name}")