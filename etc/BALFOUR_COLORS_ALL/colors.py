from os import listdir
import os.path
from os.path import isfile
from collections import OrderedDict
import datetime
from pymongo import MongoClient
import struct

from app.config import MONGO_ADDR, MONGO_PORT

CUSTOM_FOLDER = os.path.join(os.path.abspath(os.curdir), 'custom')
ORIG_FOLDER = os.path.join(os.path.abspath(os.curdir), 'original')

def get_width_and_height(img_file):
    with open(img_file, 'rb') as f:
        img_data = f.read()

    w, h = struct.unpack('>LL', img_data[16:24])
    width = float(w)
    height = float(h)

    return width, height

def get_origionals():
    files = [f for f in listdir(ORIG_FOLDER) if isfile(os.path.join(ORIG_FOLDER, f))]
    datum = []
    for orig in files:

        width, height = get_width_and_height(os.path.join(ORIG_FOLDER, orig))
        origUrl = "https://s3.amazonaws.com/myyear-openphoto/original/2015backgrounds/%s" % orig
        thumbUrl = "https://s3.amazonaws.com/myyear-openphoto/custom/2015backgrounds/%s" % orig

        bt = OrderedDict(
            ImageType='BACKGROUND',
            group='Balfour Colors',
            height=height,
            originalFileName=orig,
            originalURL=origUrl,
            photoRepoId='0',
            sheets=[],
            status="PROCESSED",
            tags=[],
            thumbnailURL=thumbUrl,
            updateDate=datetime.datetime.now(),
            version=1.0,
            width=width
        )

        datum.append(bt)
    return datum


if __name__ == "__main__":
    client = MongoClient(MONGO_ADDR, MONGO_PORT)
    db = client.myyear
    collection = db.background_images
    result = collection.insert(get_origionals())
