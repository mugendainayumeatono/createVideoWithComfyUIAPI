import csv
import logging
import random
import os

# 全局设定
log_level = logging.DEBUG
server_address_remote = "js1.blockelite.cn:21667"
server_address_remote_other = "js1.blockelite.cn:21669"
server_address_local = "127.0.0.1:8803"
server_address_local_other = "127.0.0.1:8805"
server_address = server_address_local
prompt_file_optimize = r"prompts/prompt_file_optimize.csv"
prompt_file_backdrop = r"prompts/prompt_file_backdrop.csv"
prompt_file_role = r"prompts/prompt_file_role.csv"
prompt_file_pose = r"prompts/prompt_file_pose.csv"
prompt_file_ITV = r"prompts/prompt_file_ITV.csv"
one_prompt_multi_create = 1

resolution = {
    "width": 640,
    "height": 480
}

imageMask_workflow = r"workflow/image_mask_API.json"
imageMask_input_path = r"image_input"
#direct_workflow = r"workflow/Wan_training_resource_kijai.json"
#direct_workflow = r"workflow/Wan_training_resource_org.json"
direct_workflow = r"workflow/Wan-2.1_training.json"

#flux 设定
FLUXD_output_path = "image_output"
FLUXD_workflow = r"workflow/FLUXD_v4_workflow_API.json"
prompt_file_set_picture = [prompt_file_optimize, prompt_file_backdrop, prompt_file_role, prompt_file_pose]
FLUXD_output_filename = "image_"

#wan-video 设定
wan_workflow = r"workflow/Wan-2.1_720x1280_v2.json"
wan_intput_image_path = "image_output"
wan_output_filename = "video_"
prompt_file_set_video = [prompt_file_ITV]

def set_workpath():
    """
    设置工作目录
    """
    # 获取当前脚本的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 设置工作目录为脚本所在目录
    os.chdir(script_dir)

def process_csv_to_array(file_path):
    """
    从 CSV 文件逐行读取，返回第三列之后的列
    参数：
        file_path: CSV 文件路径
    返回：
        第三列之后的列
    """
    result_array = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            logging.debug(f"读取 CSV 文件: {file_path}")
            
            for row_idx, row in enumerate(csv_reader, 1):
                if len(row) > 2:
                    if row[1] == "enable":
                        # 拼接第3列（索引2）之后的列
                        result_array.append(row[2:])
                        logging.debug(f"第 {row_idx} 行(enable): {row[2:]}")
                    else:
                        logging.debug(f"第 {row_idx} 行(disable): {row[2:]}")
                else:
                    # 少于3列时添加空字符串
                    result_array.append('0')
                    result_array.append('')
                    logging.debug(f"第 {row_idx} 行: 列数不足，添加空字符串")
            
            logging.debug(f"读取完成，共处理 {len(result_array)} 行")
            return result_array
    
    except Exception as e:
        logging.error(f"读取出错: {e}")
        return []

def split_to_lora_prompt(row):
    logging.debug(f"分割lora和提示词...")
    logging.debug(f"row = {row}")
    try:   
        # 获取第一列的数字作为字典数量
        dict_count = int(row[0])
        
        # 初始化结果列表存储字典
        lora_dicts = []
        
        # 从第2列开始，每2列创建一个字典
        # 第2列是index 1，第3列是index 2，以此类推
        for i in range(dict_count):
            # 计算列索引：每组2列，从第2列开始
            path_idx = 1 + i * 2    # lora_path的列
            strength_idx = 2 + i * 2  # strength的列
            
            # 创建字典
            lora_dict = {
                "lora_path": row[path_idx],
                "strength": float(row[strength_idx])
            }
            lora_dicts.append(lora_dict)
        
        # 获取剩余的列
        # 从第(1 + dict_count * 2)列开始到最后
        start_remain_idx = 1 + dict_count * 2
        remaining_values = row[start_remain_idx:]
        # 将剩余值用逗号连接成字符串
        remaining_string = ",".join(remaining_values)
        logging.debug(f"提示词: {remaining_values} ,lora字典: {lora_dicts}")
        return lora_dicts, remaining_string
            
    except Exception as e:
        logging.error(f"发生错误: {str(e)}")
        return [], ""

def prompt_generator_factory(prompt_file_set):
    logging.info(f"读取提示词配置...")
    prompt_arrays = []
    for each in prompt_file_set:
        prompt_arrays.append(process_csv_to_array(each))

    def _prompt_generator():
        """
        生成器函数：生成prompt
        """
        # 检查数组是否为空
        for arr in prompt_arrays:
            i= 1+1
            if not arr:
                arr.append('')
                global_vars = globals()
                for name, value in global_vars.items():
                    if isinstance(value, list) and value is arr:
                        logging.warning(f"提示词数组{arr}为空")

        while True:
            logging.info(f"生成提示词和Lora配置...")
            selected_lines = []
            selected_loras = []
            for arr in prompt_arrays:
                idx = random.choice(range(len(arr)))  # 随机选择索引
                lora,prompt = split_to_lora_prompt(arr[idx])
                selected_lines.append(prompt)
                selected_loras.extend(lora)
    
            # 拼接成字符串
            prompt = ','.join(selected_lines)
            logging.info(f"生成的提示词: {prompt}")
            logging.info(f"应加载的lora index: {selected_loras}")
            yield prompt,selected_loras
    return _prompt_generator
    
    
def get_jpg_files(directory):
    """
    获取服务器上目标目录下的所有jpg文件的绝对路径
    参数：
        directory: 服务器上目录路径
    返回：
        jpg文件绝对路径的列表
    """
    jpg_files = []
    '''
    for file in os.listdir(directory):
        if file.lower().endswith(('.jpg', '.jpeg')):
            absolute_path = os.path.abspath(os.path.join(directory, file))
            jpg_files.append(absolute_path)
    return jpg_files
    '''
    for i in range(1, 400):
        file = f"image_{i}.jpg"
        full_path = directory+"/"+(file)
        jpg_files.append(full_path)
    return jpg_files

##unit test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s')

    print("test process_csv_to_array")
    prompts = process_csv_to_array(prompt_file_role)
    print(prompts)

    print("test prompt_generator_factory")
    prompt_generator = prompt_generator_factory(prompt_file_set_video)
    prompt_gen = prompt_generator()
    for i in range(2):
        next(prompt_gen)

    print("test prompt_generator_factory")
    prompt_generator = prompt_generator_factory(prompt_file_set_picture)
    prompt_gen = prompt_generator()
    for i in range(2):
        next(prompt_gen)
