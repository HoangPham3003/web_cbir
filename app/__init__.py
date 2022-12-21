from flask import Flask
import pickle
import json


def get_features_db():
    features_file = "app/model/features.pkl"
    features_db = pickle.load(open(features_file, 'rb'))
    return features_db

def get_paths_db():
    paths_file = "app/model/paths.pkl"
    paths_db = pickle.load(open(paths_file, 'rb'))
    return paths_db

def get_db_image_class():
    db_image_class_file = "app/model/db_image_class.pkl"
    db_image_class = pickle.load(open(db_image_class_file, 'rb'))
    return db_image_class

def get_db_image_name():
    db_image_name_file = "app/model/db_image_name.pkl"
    db_image_name = pickle.load(open(db_image_name_file, 'rb'))
    return db_image_name



app = Flask(__name__)
app.secret_key = "f23sl398jhfei"


UPLOAD_FOLDER = './app/static/img_Uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['DATA_FOLDER'] = "./app/static/CorelDB1K/"


features_db = get_features_db()
paths_db = get_paths_db()
db_image_class = get_db_image_class()
db_image_name = get_db_image_name()
app.config['FEATURES_DB'] = features_db
app.config['PATHS_DB'] = paths_db
app.config['IMAGES_CLASS_DB'] = db_image_class
app.config['IMAGES_NAME_DB'] = db_image_name


from app.controller import HomeController


