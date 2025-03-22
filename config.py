import csv
import logging
import random

# 全局设定
log_level = logging.DEBUG
#server_address = "js1.blockelite.cn:21667"
server_address = "127.0.0.1:8803"
output_folder = "output"
prompt_file_optimize = r"prompts/prompt_file_optimize.csv"
prompt_file_backdrop = r"prompts/prompt_file_backdrop.csv"
prompt_file_role = r"prompts/prompt_file_role.csv"
prompt_file_pose = r"prompts/prompt_file_pose.csv"
prompt_file_ITV = r"prompts/prompt_file_ITV.csv"
one_prompt_multi_create = 1

#flux 设定
FLUXD_workflow = r"workflow/FLUXD_v2_workflow_API.json"
prompt_file_set_picture = [prompt_file_optimize, prompt_file_backdrop, prompt_file_role, prompt_file_pose]

#wan-video 设定
wan_workflow = r"workflow/wanvideo_480p_I2V_API.json"
wan_intput_image_path = "input"
#wan_intput_image_path = r"C:\userfile\02_data\AI\resource4_perprocess1_small_200\resource4_perprocess2_small_unifiedsize"
wan_output_file_name = "I2V_20250320_"
prompt_file_set_video = [prompt_file_ITV]

def process_csv_to_array(file_path, separator=','):
    """
    从 CSV 文件逐行读取，将每行第3列之后的列拼接成字符串，组成数组
    参数：
        file_path: CSV 文件路径
        separator: 拼接时的分隔符，默认为逗号
    返回：
        包含每行拼接结果的数组
    """
    result_array = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            logging.debug(f"读取 CSV 文件: {file_path}")
            
            for row_idx, row in enumerate(csv_reader, 1):
                if len(row) > 2:
                    concatenated = separator.join(row[3:])
                    if row[1] == "enable":
                        # 拼接第3列（索引2）之后的列
                        result_array.append(concatenated)
                        logging.debug(f"第 {row_idx} 行(enable): {concatenated}")
                    else:
                        logging.debug(f"第 {row_idx} 行(disable): {concatenated}")
                else:
                    # 少于3列时添加空字符串
                    result_array.append('')
                    logging.debug(f"第 {row_idx} 行: 列数不足，添加空字符串")
            
            logging.debug(f"读取完成，共处理 {len(result_array)} 行")
            return result_array
    
    except Exception as e:
        logging.error(f"读取出错: {e}")
        return []

def prompt_generator_factory(prompt_file_set):
    logging.info(f"读取提示词配置...")
    prompt_arrays = []
    for each in prompt_file_set:
        prompt_arrays.append(process_csv_to_array(each))

    def _prompt_generator():
        """
        生成器函数：生成prompt
        """
        logging.info(f"生成提示词...")

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
            # 从每个数组随机取一行
            selected_lines = [random.choice(arr) for arr in prompt_arrays]
    
            # 拼接成字符串
            result = ','.join(selected_lines)
            logging.debug(f"生成的提示词: {result}")
            yield result
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
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    prompt_generator = prompt_generator_factory(prompt_file_set_video)
    prompt_gen = prompt_generator()
    for i in range(2):
        next(prompt_gen)

    prompt_generator = prompt_generator_factory(prompt_file_set_picture)
    prompt_gen = prompt_generator()
    for i in range(2):
        next(prompt_gen)
