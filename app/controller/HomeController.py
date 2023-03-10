from app import app

import os
import time
import cv2
import json
import numpy as np

from werkzeug.utils import secure_filename
from flask import request, render_template, url_for, jsonify, redirect, session

from datetime import datetime

from PIL import Image

from tensorflow import keras
from keras.applications.vgg19 import VGG19
from keras.models import Model
from keras.utils import img_to_array
from keras.applications.densenet import preprocess_input

from sklearn import svm


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tif'}


def get_class_image(image_name):
    db_image_class = app.config['IMAGES_CLASS_DB']
    db_image_name = app.config['IMAGES_NAME_DB']
    index = db_image_name.index(image_name)
    image_class = db_image_class[index]
    return image_class
    

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =================================================================
# EXTRACT FEATURES
# =================================================================
class ExtractModel:
    def __init__(self):
        self.model = self.ModelCreator() 

    def ModelCreator(self):
        vgg19_model = VGG19(weights="imagenet")
        extract_model = Model(inputs=vgg19_model.inputs, outputs=vgg19_model.get_layer("fc2").output)
        return extract_model


def preprocessing(img):
    img = Image.fromarray(img)
    img = img.resize((224, 224))
    # img = img.convert('RGB')
    x = img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    return x


def sigmoid(x):
    a = abs(x)
    # a = 1 / (1 + math.exp(-x))
    if a >= 0.5:
        return 1
    else:
        return 0


def feature_extraction(image_path, model):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img_tensor = preprocessing(image)
    features_cnn = model.predict(img_tensor)[0]
    sigmoid_v = np.vectorize(sigmoid)
    features = sigmoid_v(features_cnn)
    return features

# =================================================================
# SEARCH ENGINE AND RELEVANCE FEEDBACK
# =================================================================
def search_image(query_image_path, model):
    features_db = app.config['FEATURES_DB']
    paths_db = app.config['PATHS_DB']
    query_image_features = feature_extraction(image_path=query_image_path, model=model)
    # print(query_image_features.shape)
    
    distances = (1/4096) * np.linalg.norm(features_db - query_image_features, ord=1, axis=1)
    # distances = np.linalg.norm(features_db - query_image_features, axis=1)
    K = 100
    indexs = np.argsort(distances)[:K]

    nearest_images = [(features_db[id].tolist(), paths_db[id], distances[id]) for id in indexs]
    
    return query_image_features, nearest_images


def find_labeled_data(query_image_path, nearest_images):
    arr_split = query_image_path.split("__")
    temp = arr_split[0].split('/')
    class_query_image = temp[-1]

    labeled_data = []

    n_pos = 0
    n_neg = 0
    for img in nearest_images:
        paths_img = img[1]
        x_vector = None
        y_label = None
        if class_query_image in paths_img:
            x_vector = img[0]
            y_label = 1
            n_pos += 1
        else:
            x_vector = img[0]
            y_label = 0
            n_neg += 1
        labeled_data.append((x_vector, y_label, img[1]))
    return labeled_data, n_pos, n_neg


def find_unlabeled_data(nearest_images):
    features_db = app.config['FEATURES_DB']
    paths_db = app.config['PATHS_DB']

    paths_nearest_img = []
    for img in nearest_images:
        paths_nearest_img.append(img[1])
    
    unlabeled_img_indexs = []
    for i in range(len(paths_db)):
        path = paths_db[i]
        if path not in paths_nearest_img:
            # unlabeled_img_indexs.append(features_db[i])
            unlabeled_img_indexs.append(i)
    return unlabeled_img_indexs


def compute_DS(svc, unlabeled_data_indexs):
    features_db = app.config['FEATURES_DB']
    DS_arr = []
    for i in range(len(unlabeled_data_indexs)):
        idx = unlabeled_data_indexs[i]
        x = features_db[idx]
        x = x.reshape(1, -1)
        dist = abs(svc.decision_function(x))
        # w_norm = np.linalg.norm(svc.coef_)
        # dist = y / w_norm
        DS_arr.append(dist)
    return DS_arr


def compute_DE(svc, query_image_features, unlabeled_data_indexs):
    features_db = app.config['FEATURES_DB']
    DE_arr = []
    for i in range(len(unlabeled_data_indexs)):
        idx = unlabeled_data_indexs[i]
        x = features_db[idx]
        x = x.reshape(1, -1)
        t = svc.decision_function(x)
        if t >= 0:
            dist = np.linalg.norm(x - query_image_features)
        else:
            dist = int(1e9)
        DE_arr.append(dist)
    return DE_arr


def compute_DSE(unlabeled_data_indexs, n_pos, n_neg, DS_arr, DE_arr):
    DSE_arr = []
    for i in range(len(unlabeled_data_indexs)):
        DS_idx = DS_arr[i]
        DE_idx = DE_arr[i]
        dse = (n_pos/(n_pos+n_neg)) * DS_idx + (1-(n_pos/(n_pos+n_neg))) * DE_idx
        DSE_arr.append(dse)
    return DSE_arr


def svm_active_learning(clf, labeled_data, n_pos, n_neg, unlabeled_data_indexs, query_image_features, query_image_path, nearest_images):

    temp_unlabeled_data_indexs = unlabeled_data_indexs.copy()
    
    # print(f"n_pos : {n_pos} ====== n_neg : {n_neg}")

    X_train = []
    y_train = []
    for d in labeled_data:
        X_train.append(d[0])
        y_train.append(d[1])

    k = 100
    # define classifier
    clf.fit(X_train, y_train)

    DS_arr = compute_DS(clf, temp_unlabeled_data_indexs)
    DE_arr = compute_DE(clf, query_image_features, temp_unlabeled_data_indexs)

    future_labels = []
    for _ in range(k):
        DSE_arr = compute_DSE(temp_unlabeled_data_indexs, n_pos, n_neg, DS_arr, DE_arr)

        DSE_arr = np.array(DS_arr)
        min_dist_index = np.argmin(DSE_arr) # active learning: find the data point closest from boudary

        idx = temp_unlabeled_data_indexs[min_dist_index]
        future_labels.append(idx) # S* set: data to label
        temp_unlabeled_data_indexs.pop(min_dist_index)
        DS_arr.pop(min_dist_index)
        DE_arr.pop(min_dist_index)
    
    return clf, future_labels


def update_nearest_image(clf, query_image_features, query_image_path, old_nearest_images, future_labels):

    features_db = app.config['FEATURES_DB']
    paths_db = app.config['PATHS_DB']

    arr_split = query_image_path.split("__")
    temp = arr_split[0].split('/')
    class_query_image = temp[-1]

    images = []
    n_pos = 0
    n_neg = 0

    # classify old nearest images: 1 (relevant), 0 (non-relevant)
    for img in old_nearest_images:
        features_img = img[0]
        paths_img = img[1]
        if class_query_image in paths_img:
            n_pos += 1
            images.append((features_img, paths_img, 1, 1)) # images[i]: (features_vector, path_image, rel/non_rel - 1/0, old/new positive - 1/0)
        else:
            n_neg += 1
            images.append((features_img, paths_img, 0, 1))

    # labeling new labels from svm-active-learning algorithm
    for i in future_labels:
        x = features_db[i]
        x = x.reshape(1, -1)
        y_hat = clf.predict(x)[0]
        if y_hat == 1:
            n_pos += 1
            images.append((features_db[i].tolist(), paths_db[i], 1, 0))
        else:
            n_neg += 1
            images.append((features_db[i].tolist(), paths_db[i], 0, 0))


    ds_arr = []
    de_arr = []
    dse_arr = []
    old_postive = []


    # save old positive
    for i in range(len(images)):
        img = images[i]
        rel_or_not = img[2] # 1 (rel), 0 (non-rel)
        old_or_not = img[3] # 1 (old), 0 (new)
        if rel_or_not == 1 and old_or_not == 1: # old positive
            old_postive.append(i)

    # compute DS
    for img in images:
        features = np.array(img[0], dtype=np.float64)
        features = features.reshape(1, -1)
        path = img[1]
        dist = abs(clf.decision_function(features))
        # w_norm = np.linalg.norm(svc.coef_)
        # dist = y / w_norm
        ds_arr.append(dist)

    # compute DE
    for img in images:
        features = np.array(img[0], dtype=np.float64)
        features = features.reshape(1, -1)
        # t = clf.decision_function(features)
        if img[2] == 1:
            dist = np.linalg.norm(features - query_image_features)
        else:
            dist = int(1e9)
        de_arr.append(dist)

    # compute DSE
    for i in range(len(images)):
        if i in old_postive:
            alpha = 1/4
        else:
            alpha = 4
        DS_idx = ds_arr[i]
        DE_idx = de_arr[i]
        dse = 0.3 * DS_idx + 0.7 * DE_idx
        # dse = (n_pos/(n_pos+n_neg)) * DS_idx + (1-(n_pos/(n_pos+n_neg))) * DE_idx
        dse = dse * alpha # ensure that old positive will be presented at first
        dse_arr.append(dse)

    dse_arr = np.array(dse_arr)
    dse_arr = dse_arr.reshape(-1)
    K = 100
    indexs = np.argsort(dse_arr)[:K]

    nearest_images = [(images[id][0], images[id][1], dse_arr[id]) for id in indexs]
    return nearest_images


def update_current_labeled_data(query_image_path, current_labeled_data, current_n_pos, current_n_neg, new_nearest_images):
    temp_labeled_data_set, temp_n_pos, temp_n_neg = find_labeled_data(query_image_path, new_nearest_images)

    arr_path_current_labeled_data = []
    for labeled_data in current_labeled_data:
        path = labeled_data[2]
        arr_path_current_labeled_data.append(path)

    counter = 0
    for temp_labeled_data in temp_labeled_data_set:
        pos_or_neg = temp_labeled_data[1]
        path_temp_labeled_data = temp_labeled_data[2]
        if path_temp_labeled_data not in arr_path_current_labeled_data:
            current_labeled_data.append(temp_labeled_data)
            if pos_or_neg == 1:
                current_n_pos += 1
            elif pos_or_neg == 0:
                current_n_neg += 1
            counter += 1
    # print(counter)
    return current_labeled_data, current_n_pos, current_n_neg


def update_current_unlabeled_data_indices(current_labeled_data, current_unlabeled_data_indices):
    # print(f"==== {len(current_unlabeled_data_indices)}")
    paths_db = app.config['PATHS_DB']

    for labeled_data in current_labeled_data:
        path = labeled_data[2]
        paths_db_index = paths_db.index(path)
        if paths_db_index in current_unlabeled_data_indices:
            current_unlabeled_data_indices.remove(paths_db_index)
    return current_unlabeled_data_indices


# =================================================================
# WEB RUNNING
# =================================================================

@app.route("/favicon.ico")
def favicon():
    return "", 200


@app.route("/", methods=['GET', 'POST'])
# @SystemController.check_acl
def home():
    kernel = 'rbf'
    clf = svm.SVC(kernel=kernel)

    vgg19_model = ExtractModel().model

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            clf = svm.SVC(kernel=kernel)
            
            fileName = secure_filename(file.filename)

            image_class = get_class_image(fileName)
            file_name, file_extension = fileName.split('.')
            
            now = datetime.now()
            dt_string = now.strftime("__%d_%m_%Y_%H_%M_%S")
            fileName = image_class + '__' + file_name + dt_string + '.' + file_extension
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fileName))

            file_path = "./app/static/img_Uploads/" + str(fileName)
            
            query_image_path = file_path
            start_time = time.time()
            query_image_features, nearest_images = search_image(query_image_path=query_image_path, model=vgg19_model)
            end_time = time.time()

            data = {}
            db_images = []
            for img in nearest_images:
                img_path = img[1]
                img_path_split = img_path.split('/')
                image_class = img_path_split[-2]
                image_name = img_path_split[-1]
                image_info = {
                    "class": image_class,
                    "name": image_name,
                    "features": img[0]
                }
                db_images.append(image_info)

            data['show_nearest_images'] = db_images # class, name, features
            data['nearest_images'] = nearest_images # features, path, distance
            data['query_path'] = file_path
            data['query_features'] = query_image_features.tolist()

            labeled_data_set, n_pos, n_neg = find_labeled_data(query_image_path, nearest_images)
            unlabeled_data_set_indices = find_unlabeled_data(nearest_images)

            data['n_pos'] = n_pos
            data['n_neg'] = n_neg
            data['labeled_data_set'] = labeled_data_set
            data['unlabeled_data_set_indices'] = unlabeled_data_set_indices
            
            
            run_time = str(end_time - start_time) + " (s)"
            data['run_time'] = run_time

            return jsonify(data=data)
    elif request.method == 'POST' and 'relevance_feedback' in request.form:
        print()
        print("====================> STARTING RELEVANCE FEEDBACK")
        print()
        
        data = json.loads(request.form['relevance_feedback'])

        query_path = data['query_path'] # ./app/static/img_Uploads/wl_horse__113007__05_12_2022_16_14_38.jpg
        query_features = np.array(data['query_features'], dtype=np.float64) # list 4096
        nearest_images = data['nearest_images'] # dict: class, features (list), name
        n_pos = int(data['n_pos']) # int
        n_neg = int(data['n_neg']) # int
        labeled_data_set = data['labeled_data_set'] # list
        unlabeled_data_set_indices = data['unlabeled_data_set_indices'] #list

        # relevance feedback
        start_time = time.time()
        clf, future_labels = svm_active_learning(clf, labeled_data_set, n_pos, n_neg, unlabeled_data_set_indices, query_features, query_path, nearest_images)
        nearest_images = update_nearest_image(clf, query_features, query_path, nearest_images, future_labels)
        labeled_data_set, n_pos, n_neg = update_current_labeled_data(query_path, labeled_data_set, n_pos, n_neg, nearest_images)
        unlabeled_data_set_indices = update_current_unlabeled_data_indices(labeled_data_set, unlabeled_data_set_indices)
        end_time = time.time()
        # return db_images for show_nearest_images in JS, HTML
        data = {}
        db_images = []
        for img in nearest_images:
            img_path = img[1]
            img_path_split = img_path.split('/')
            image_class = img_path_split[-2]
            image_name = img_path_split[-1]
            image_info = {
                "class": image_class,
                "name": image_name,
                "features": img[0]
            }
            db_images.append(image_info)

        data['show_nearest_images'] = db_images # class, name, features
        data['nearest_images'] = nearest_images # features, path, distance
        data['query_path'] = query_path
        data['query_features'] = query_features.tolist()
        data['n_pos'] = n_pos
        data['n_neg'] = n_neg
        data['labeled_data_set'] = labeled_data_set
        data['unlabeled_data_set_indices'] = unlabeled_data_set_indices

        
        run_time = str(end_time - start_time) + " (s)"
        data['run_time'] = run_time

        return jsonify(data=data)

    return render_template('home.html')
