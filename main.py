#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import io
from pathlib import Path
import logging
import os
import random
from datetime import datetime

import config
import workflow

def queue_prompt(prompt):
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

def get_images(ws, prompt):
    logging.info(f"开始生成图片...")
    prompt.set_workflow_param()
    prompt_id = queue_prompt(prompt.prompt_json)['prompt_id']
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

def save_images(images, folder):
    logging.info(f"保存图片...")
    folder_path = Path(folder)
    try:
        folder_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"{e}")

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for node_id in images:
        file_path = os.path.join(folder, f"{current_time}.png")
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            image.save(file_path)
            #image.show()

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    logging.info(f"初始化...")
    client_id = str(uuid.uuid4())
    obj_workflow = workflow.workflow_wan(config.wan_workflow)
    #obj_workflow = workflow.workflow(config.FLUXD_workflow)
    prompt_words = config.prompt_generator()

    logging.info(f"连接服务器...")
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(config.server_address, client_id))
    logging.info(f"成功")

    while True:
        try:
            obj_workflow.set_workflow_prompt_word(next(prompt_words))
        except StopIteration:
            logging.info("已经没有更多的prompt了,结束程序")
            break

        create_counter=0
        image_list = config.get_jpg_files(config.wan_intput_image_path)
        for each_image in image_list:
            create_counter=create_counter+1
            if create_counter>config.create_limit and config.create_limit != -1:
                logging.info("达到每个提示词尝试图片的上限({config.create_limit}),结束当前prompt")
                break
            logging.info(f"第{create_counter}张图片")
            obj_workflow.set_workflow_source_image(each_image)
            for i in range(config.one_prompt_drew_time):
                images = get_images(ws, obj_workflow)
                #save_images(images, config.output_folder)
                pass
    ws.close()

