#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s')
import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import cv2
import io
from pathlib import Path
import os
from datetime import datetime
from requests_toolbelt import MultipartEncoder

import config
import workflow

def queue_prompt(prompt, client_id):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(config.server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(config.server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(config.server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt, client_id):
    logging.info(f"开始生成图片...")
    prompt.set_workflow_param_every_loop()
    prompt_id = queue_prompt(prompt.prompt_json,client_id)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            # If you want to be able to decode the binary stream for latent previews, here is how you can do it:
            # bytesIO = BytesIO(out[8:])
            # preview_image = Image.open(bytesIO) # This is your preview in PIL image format, store it in a global
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
        output_images[node_id] = images_output

    logging.info(f"完成...")
    return output_images

def get_videos(ws, prompt, client_id):
    logging.info(f"开始生成视频...")
    prompt.set_workflow_param_every_loop()
    prompt_id = queue_prompt(prompt.prompt_json,client_id)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'gifs' in node_output:
            for image in node_output['gifs']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
        output_images[node_id] = images_output

    logging.info(f"完成...")
    return output_images

def save_file(images, folder, type="image"):
    logging.info(f"保存文件...")
    folder_path = Path(folder)
    try:
        folder_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"{e}")

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for node_id in images:
        if type=="image":
            file_path = os.path.join(folder, f"{config.FLUXD_output_filename}_{current_time}.png")
        elif type=="video":
            file_path = os.path.join(folder, f"{config.wan_output_filename}_{current_time}.MP4")
        else:
            logging.error(f"不支持保存类型{type}")
            return
        for image_data in images[node_id]:
            if type=="image":
                image = Image.open(io.BytesIO(image_data))
                image.save(file_path)
                #image.show()
            elif type=="video":
                #cap = cv2.VideoCapture(io.BytesIO(image_data))
                cap = cv2.VideoCapture(image_data)
                if not cap.isOpened():
                    logging.error("错误：无法打开视频文件")
                    return
                # 获取视频属性
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
                # 定义视频编码器
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 编码
                out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                # 释放资源
                cap.release()
                out.release()
                cv2.destroyAllWindows()

def save_multi_file(images, base_folder, filename, type="image"):
    logging.info(f"保存文件...")
    folder_dict_list = {}
    base_path = Path(base_folder)
    base_folder_dict_list = workflow.workflow_imageMask.folder_dict_list
    for key,value in base_folder_dict_list.items():
        folder_dict_list[key] = base_path / value["folder"]
        try:
            folder_dict_list[key].mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"{e}")

    for node_id in images:
        if base_folder_dict_list[node_id]["type"] == "images":
            file_path = os.path.join(folder_dict_list[node_id], f"{node_id}_nomask_{filename}")
        elif base_folder_dict_list[node_id]["type"] == "mask":
            file_path = os.path.join(folder_dict_list[node_id], f"{node_id}_{filename}")
        else:
            logging.error(f"不支持保存类型{folder_dict_list[node_id]["type"]}")
            return
        for image_data in images[node_id]:
            if type=="image":
                image = Image.open(io.BytesIO(image_data))
                image.save(file_path,"PNG")
                logging.error(f"已保存文件{file_path}")
                #image.show()


def upload_image(input_path, name, image_type="input", overwrite=False):
    """
    Uploads an image to ComfyUI using multipart/form-data encoding.

    This function opens an image file from the specified path and uploads it to running ComfyUI. The server's address,
    the name to save the image as, and optional parameters for image type and overwrite behavior are provided as arguments.
    The image is uploaded as 'image/png'.

    Args:
    input_path (str): The file system path to the image file to be uploaded.
    name (str): The name under which the image will be saved on ComfyUI.
    server_address (str): The address of running ComfyUI where the image will be uploaded, excluding the protocol prefix.
    image_type (str, optional): The type/category of the image being uploaded. Defaults to "input". Other options are "output" and "temp".
    overwrite (bool, optional): Flag indicating whether an existing file with the same name should be overwritten.
    Defaults to False.

    Returns:
    The ComfyUI response to the upload request.
    """

    with open(input_path, 'rb') as file:
        multipart_data = MultipartEncoder(
            fields= {
            'image': (name, file, 'image/png'),
            'type': image_type,
            'overwrite': str(overwrite).lower()
            }
        )
        data = multipart_data
        headers = { 'Content-Type': multipart_data.content_type }
    
        request = urllib.request.Request("http://{}/upload/image".format(config.server_address), data=data, headers=headers)
        with urllib.request.urlopen(request) as response:
            return response.read()

def  create_picture(create_num=10):
    logging.info(f"初始化...")
    client_id = str(uuid.uuid4())
    obj_workflow = workflow.workflow(config.FLUXD_workflow)
    prompt_generator = config.prompt_generator_factory(config.prompt_file_set_picture)
    prompt_words = prompt_generator()

    logging.info(f"连接服务器...")
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(config.server_address, client_id))
    logging.info(f"成功")

    create_counter=0
    obj_workflow.set_workflow_param_init()
    while True:
        create_counter=create_counter+1
        if create_counter>create_num:
            logging.info(f"完成，已创建({create_num}张)")
            break
        try:
            prompt,selected_loras = next(prompt_words)
            obj_workflow.set_workflow_PowerLoraLoader(selected_loras)
            obj_workflow.set_workflow_prompt_word(prompt)
        except StopIteration:
            logging.info("已经没有更多的prompt了,结束程序")
            break

        for i in range(config.one_prompt_multi_create):
            images = get_images(ws, obj_workflow, client_id)
            save_file(images, config.FLUXD_output_path)
            pass
    ws.close()
    return create_counter

def create_video_ITV(create_num=10):
    logging.info(f"初始化...")
    client_id = str(uuid.uuid4())
    obj_workflow = workflow.workflow_wan(config.wan_workflow)
    prompt_generator = config.prompt_generator_factory(config.prompt_file_set_video)
    prompt_words = prompt_generator()

    logging.info(f"连接服务器...")
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(config.server_address, client_id))
    logging.info(f"成功")

    #使用服务器上的文件
    #jpg_files = config.get_jpg_files(config.wan_intput_image_path)
    #上传本地文件
    dir_path = Path(config.wan_intput_image_path)
    jpg_files = list(dir_path.rglob("*.[jJ][pP][gG]"))  # 支持大小写
    jpg_files.extend(dir_path.rglob("*.[jJ][pP][eE][gG]"))  # 支持 .jpeg
    jpg_files.extend(dir_path.rglob("*.[pP][nN][gG]"))  # 支持 .jpeg
    # 依次处理每个文件
    create_counter=0
    obj_workflow.set_workflow_param_init()
    for jpg_file in jpg_files:
        create_counter=create_counter+1
        if create_counter>create_num:
            break
        absolute_path = jpg_file.absolute()
        file_name = jpg_file.name  # 获取文件名，例如 "image1.jpg"
        logging.info("上传图片...")
        upload_image(str(absolute_path), file_name, "input", True)
        logging.debug(f"{absolute_path}")
        obj_workflow.set_workflow_source_image(file_name)
        #生成提示词
        try:
            prompt,selected_loras = next(prompt_words)
            obj_workflow.set_workflow_PowerLoraLoader(selected_loras)
            obj_workflow.set_workflow_prompt_word(prompt)
        except StopIteration:
            logging.info("已经没有更多的prompt了,结束程序")
            break
        obj_workflow.write_json_file(f"workflow_output_{create_counter}.json")
        for i in range(config.one_prompt_multi_create):
            images = get_videos(ws, obj_workflow,client_id)
            #save_file(images, config.output_folder, "video")
    logging.info(f"完成，已创建({create_counter})")
    ws.close()


def  create_from_workflow_direct(type="image",create_num=10):
    logging.info(f"初始化...")
    client_id = str(uuid.uuid4())
    obj_workflow = workflow.workflow(config.direct_workflow)
    prompt_generator = config.prompt_generator_factory(config.prompt_file_set_picture)
    prompt_words = prompt_generator()

    logging.info(f"连接服务器...")
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(config.server_address, client_id))
    logging.info(f"成功")

    create_counter=0
    while True:
        create_counter=create_counter+1
        if create_counter>create_num:
            logging.info(f"完成，已创建({create_num}张)")
            break

        for i in range(config.one_prompt_multi_create):
            if(type == "image"):
                images = get_images(ws, obj_workflow, client_id)
                save_file(images, config.FLUXD_output_path)
            elif(type == "video"):
                images = get_videos(ws, obj_workflow,client_id)
            pass
    ws.close()
    return create_counter

def  creat_imageMask(create_num=10):
    logging.info(f"初始化...")
    client_id = str(uuid.uuid4())
    obj_workflow = workflow.workflow_imageMask(config.imageMask_workflow)

    logging.info(f"连接服务器...")
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(config.server_address, client_id))
    logging.info(f"成功")

        #使用服务器上的文件
    #jpg_files = config.get_jpg_files(config.wan_intput_image_path)
    #上传本地文件
    dir_path = Path(config.imageMask_input_path)
    jpg_files = list(dir_path.rglob("*.[jJ][pP][gG]"))  # 支持大小写
    jpg_files.extend(dir_path.rglob("*.[jJ][pP][eE][gG]"))  # 支持 .jpeg
    jpg_files.extend(dir_path.rglob("*.[pP][nN][gG]"))  # 支持 .jpeg

    # 依次处理每个文件
    create_counter=0
    for jpg_file in jpg_files:
        create_counter=create_counter+1
        if create_counter>create_num:
            break
        absolute_path = jpg_file.absolute()
        file_name = jpg_file.name  # 获取文件名，例如 "image1.jpg"
        logging.info("上传图片...")
        upload_image(str(absolute_path), file_name, "input", True)
        logging.debug(f"{absolute_path}")
        obj_workflow.set_workflow_source_image(file_name)

        images = get_images(ws, obj_workflow, client_id)
        save_multi_file(images, config.FLUXD_output_path, file_name, type="image")

    logging.info(f"完成，已创建({create_counter})")

    ws.close()
    return create_counter


if __name__ == "__main__":
    num = 100
    create_num = 100
    #create_num = create_picture(num)
    #create_num = create_from_workflow_direct(create_num = num)
    #create_video_ITV(create_num)# 每张11分钟，32张大概6小时完成

    creat_imageMask(create_num = num)


