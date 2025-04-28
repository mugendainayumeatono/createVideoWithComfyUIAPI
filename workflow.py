import logging
import json
import random
from datetime import datetime

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

    def set_workflow_param_every_loop(self):
        logging.info(f"设置参数...")
        logging.info(f"设置KSampler随机seed")
        # 生成 0 到 2^64-1 之间的随机整数（8 字节）
        random_int = random.randrange(0, 2**64)
        nodeNum = self.searchWorkflowNode("KSampler")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["seed"] = random_int
            logging.debug(f"set seed = {random_int}")

    def set_workflow_param_init(self):
        logging.info(f"初始化参数...")
        self.set_workflow_resolution(config.resolution)
    
    def set_workflow_PowerLoraLoader(self, lora_sets):
        count = 0
        def create_lora_config(lora_index, lora_path, strength=1, on=True):
            new_lora = {
                lora_index: {
                "on": on,
                "lora": lora_path,
                "strength": strength
                }
            }
            return new_lora
        
        logging.info(f"设置lora")
        logging.debug(lora_sets)
        nodeNum = self.searchWorkflowNode("Power Lora Loader (rgthree)")
        for lora in lora_sets:
            count = count +1
            lora_index = f"lora_{count}"
            logging.debug(f"set {lora_index}")
            logging.debug(f"lora_path:{lora["lora_path"]}")
            logging.debug(f"strength:{lora["strength"]}")
            new_lora = create_lora_config(lora_index, lora["lora_path"], lora["strength"])
            self.prompt_json[nodeNum]["inputs"].update(new_lora)

    def set_workflow_source_image(self,imagePatch):
        logging.info(f"设置图片源...")
        nodeNum = self.searchWorkflowNode("LoadImage")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["image"] = imagePatch
            logging.debug(f"use image = {imagePatch}")

    def set_workflow_resolution(self, resolution):
        logging.info(f"设置分辨率...")
        nodeNum = self.searchWorkflowNode("EmptySD3LatentImage")
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["width"] = resolution["width"]
            self.prompt_json[nodeNum]["inputs"]["height"] = resolution["height"]
            logging.debug(f"set resolution = {resolution}")

    # 写入 JSON 文件  
    def write_json_file(self, file_path):
        # 获取默认的根日志器
        logger = logging.getLogger()
        # 获取当前有效的日志等级
        current_level = logger.getEffectiveLevel()
        if current_level == logging.DEBUG:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    # pretty print 格式化输出，indent=4 是缩进4个空格
                    json.dump(self.prompt_json, file, ensure_ascii=False, indent=4)
                logging.info(f"成功写入文件：{file_path}")
            except Exception as e:
                logging.error(f"写入文件时出错：{e}")


class workflow_wan(workflow):
    def set_workflow_prompt_word(self,prompt_word):
        logging.info(f"设置提示词...")
        
        nodeNum = self.searchWorkflowNode("CLIPTextEncode")
        nodeNum = "14" ## 暂时用hardcode
        if nodeNum is not None:
            self.prompt_json[nodeNum]["inputs"]["text"] = prompt_word
            logging.debug(f"set prompt = {prompt_word}")

    def set_workflow_param_init(self):
        logging.info(f"初始化参数...")
        nodeNum = self.searchWorkflowNode("VHS_VideoCombine")
        if nodeNum is not None:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.prompt_json[nodeNum]["inputs"]["filename_prefix"] = f"{config.wan_output_filename}_{current_time}"
            logging.debug(f"set output file name = {config.wan_output_filename}_{current_time}")


class workflow_imageMask(workflow):

    folder_dict_list = {
            "34":
            {
                "type": "images",
                "folder": "face"
            },
            "24":
            {
                "type": "mask",
                "folder": "clothing"
            },
            "23":
            {
                "type": "images",
                "folder": "clothing"
            },
            "22":
            {
                "type": "mask",
                "folder": "face"
            },
            "18":
            {
                "type": "mask",
                "folder": "removeBackground"
            },
            "16":
            {
                "type": "images",
                "folder": "removeBackground"
            },
    }
    
    def set_workflow_param_every_loop(self):
        pass

class workflow_direct(workflow):
    def set_workflow_param_every_loop(self):
        pass

##unit test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s')
    obj_workflow = workflow(config.FLUXD_workflow)
    prompt_generator = config.prompt_generator_factory(config.prompt_file_set_picture)
    prompt_gen = prompt_generator()
    prompt,selected_loras = next(prompt_gen)
    obj_workflow.set_workflow_PowerLoraLoader(selected_loras)
    obj_workflow.set_workflow_prompt_word(prompt)
    print(obj_workflow.prompt_json)