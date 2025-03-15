import csv
import logging
import os

server_address = "js1.blockelite.cn:21667"
FLUXD_workflow = r"workflow\FLUXD_v1_workflow.json"
wan_workflow = r"workflow\wanvideo_480p_I2V_API.json"
output_folder = "output"
prompt_file = "prompt.csv"
one_prompt_drew_time = 1
wan_intput_image_path = "/home/hdd1/sd-scripts/resource/resource4_perprocess1_small_unifiedsize"
wan_output_file_name = "create_test"
create_limit = 3

def prompt_generator(file_path = None, separator=','):
    """
    生成器函数：逐行读取CSV文件，将第3列以后的内容拼接成字符串
    参数：
        file_path: CSV文件路径
    产出：
        每行的拼接结果字符串
    """
    if file_path is None:
        file_path = prompt_file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if len(row) > 2:
                    # 将第3列以后的内容用separator拼接
                    concatenated = separator.join(row[2:])
                    yield concatenated
                else:
                    yield ''
                    
    except Exception as e:
        logging.error(f"{e}")
        return
    
def get_jpg_files(directory):
    """
    参数：
        directory: 目标目录路径
    返回：
        jpg文件绝对路径的列表
    """
    jpg_files = [""]
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