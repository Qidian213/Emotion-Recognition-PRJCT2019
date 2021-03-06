import cv2
from utils.transforms import ImageToTensor
import torch
import numpy as np
import os
from utils.utils import xywh2xyxy, from_yolo_target
from data.detection.show_targets import show_rectangles
import time
from torchvision.transforms import ToTensor


def bbox_resize(coords, from_shape, to_shape):
    new_coords = list()
    new_coords.append(int(coords[0] * (to_shape[0] / from_shape[0])))
    new_coords.append(int(coords[1] * (to_shape[1] / from_shape[1])))
    new_coords.append(int(coords[2] * (to_shape[0] / from_shape[0])))
    new_coords.append(int(coords[3] * (to_shape[1] / from_shape[1])))
    return new_coords


PATH_TO_DETECTION_MODEL = 'log\\detection\\20.01.13_12-53'
PATH_TO_RECOGNITION_MODEL = 'log\\emorec\\20.01.25_03-16'
emotions = ['Anger', 'Happy', 'Neutral', 'Surprise']
DETECTION_SHAPE = (320, 320)
EMOREC_SHAPE = (64, 64)
DETECTION_TRESHOLD = 0.4


detection_model = torch.load(os.path.join(PATH_TO_DETECTION_MODEL, 'model.pt'))
detection_load = torch.load(os.path.join(PATH_TO_DETECTION_MODEL, 'checkpoint.pt'))
detection_model.load_state_dict(detection_load['model_state_dict'])

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

detection_model.to(device)
detection_model.eval()

recognition_model = torch.load(os.path.join(PATH_TO_RECOGNITION_MODEL, 'detection_model.pt'))
recognition_load = torch.load(os.path.join(PATH_TO_RECOGNITION_MODEL, 'checkpoint.pt'))
recognition_model.load_state_dict(recognition_load['model_state_dict'])

recognition_model.to(device)
recognition_model.eval()

detection_predict = []
handling_detection = []
recognition_predict = []
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, image = cap.read()
    orig_shape = image.shape[:2]  # (480, 640)
    start = time.time()

    detection_image = cv2.resize(image, DETECTION_SHAPE)
    detection_image = ImageToTensor()(detection_image).to(device)
    detection_image = detection_image.unsqueeze(0)
    output = detection_model(detection_image)

    listed_output = from_yolo_target(output[:, :10, :, :], detection_image.size(2), grid_size=5, num_bboxes=2)
    pred_output = listed_output[:, np.argmax(listed_output[:, :, 4]).item(), :]
    pred_xyxy = xywh2xyxy(pred_output[:, :4])

    if pred_output[:, 4][0] > DETECTION_TRESHOLD:

        bbox_h = pred_xyxy[3] - pred_xyxy[1]
        bbox_x_center = (pred_xyxy[0] + pred_xyxy[2]) // 2

        bbox_l_y = int((pred_xyxy[1]) * (orig_shape[0] / DETECTION_SHAPE[1]))  # Make bbox square with sides equal to
        bbox_r_y = int((pred_xyxy[3]) * (orig_shape[0] / DETECTION_SHAPE[1]))  # bbox height. And transform its coords

        bbox_l_x = int((bbox_x_center - bbox_h // 2) * (orig_shape[1] / DETECTION_SHAPE[0]))  # correspondingly to
        bbox_r_x = int((bbox_x_center + bbox_h // 2) * (orig_shape[1] / DETECTION_SHAPE[0]))  # DETECTION_SHAPE -> orig_shape

        bbox_l_y = np.clip(bbox_l_y, 0, orig_shape[0])
        bbox_r_y = np.clip(bbox_r_y, 0, orig_shape[0])
        bbox_l_x = np.clip(bbox_l_x, 0, orig_shape[1])
        bbox_r_x = np.clip(bbox_r_x, 0, orig_shape[1])

        face_image = image[bbox_l_y:bbox_r_y, bbox_l_x:bbox_r_x, :]
        face_image = cv2.resize(face_image, EMOREC_SHAPE, EMOREC_SHAPE)
        face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        face_image = ToTensor()(face_image).unsqueeze(0).to(device)

        pred_emo = recognition_model(face_image).argmax(dim=1).item()

        show_rectangles(image,
                        np.expand_dims(np.array(bbox_resize(pred_xyxy, DETECTION_SHAPE, orig_shape[::-1])), axis=0),
                        [emotions[pred_emo]])
    else:
        cv2.imshow('image', image)
    fps = 1. / (time.time() - start)
    print(fps)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()


