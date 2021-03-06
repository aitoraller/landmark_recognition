# USAGE
# python extract_features.py --dataset ../datasets/animals/images \
# 	--output ../datasets/animals/hdf5/features.hdf5
# python extract_features.py --dataset ../datasets/caltech-101/images \
# 	--output ../datasets/caltech-101/hdf5/features.hdf5
# python extract_features.py --dataset ../datasets/flowers17/images \
#	--output ../datasets/flowers17/hdf5/features.hdf5

# import the necessary packages
from keras.applications import ResNet50
from keras.applications import imagenet_utils
from keras.preprocessing.image import img_to_array
from keras.preprocessing.image import load_img
from sklearn.preprocessing import LabelEncoder
from store import HDF5DatasetWriter
from imutils import paths
import numpy as np
import progressbar
import argparse
import random
import os
import csv

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--data_file", required=True, help="path to input csv data file")
ap.add_argument("-i", "--images_folder", required=True, help="path to input images folder")
ap.add_argument("-o", "--output", required=True, help="path to output HDF5 file")
ap.add_argument("-b", "--batch-size", type=int, default=32, help="batch size of images to be passed through network")
ap.add_argument("-s", "--buffer-size", type=int, default=1000, help="size of feature extraction buffer")
args = vars(ap.parse_args())

# store the batch size in a convenience variable
bs = args["batch_size"]

# grab the list of images that we'll be describing then randomly
# shuffle them to allow for easy training and testing splits via
# array slicing during training time
print("[INFO] loading images...")
# imagePaths = list(paths.list_images(args["dataset"]))
# random.shuffle(imagePaths)

# extract the class labels from the image paths then encode the
# labels
# labels = [p.split(os.path.sep)[-2] for p in imagePaths]
# le = LabelEncoder()
# labels = le.fit_transform(labels)


data_file = args["data_file"]
csvfile = open(data_file, 'r')
csvreader = csv.reader(csvfile)
key_url_list = [line[:3] for line in csvreader]
key_url_list = key_url_list[1:]  # Remove titles

images_folder = args["images_folder"]
imagePathsReal = list(paths.list_images(images_folder))
data_label = [[os.path.join(images_folder, '%s.jpg' % key), label] for [key, url, label] in key_url_list
              if os.path.isfile(os.path.join(images_folder, '%s.jpg' % key))]
data_label = np.asarray(data_label)

print(len(key_url_list))
print(len(imagePathsReal))
print(data_label.shape)

imagePaths = data_label[:, 0]
labels = data_label[:, 1]
le = LabelEncoder()
labels = le.fit_transform(labels)

# load the ResNet50 network
print("[INFO] loading network...")
model = ResNet50(weights="imagenet", include_top=False)
# model.summary()

# initialize the HDF5 dataset writer, then store the class label
# names in the dataset
dataset = HDF5DatasetWriter((len(imagePaths), 2048), args["output"], dataKey="features",
                            bufSize=args["buffer_size"])
# dataset.storeClassLabels(le.classes_)

# initialize the progress bar
widgets = ["Extracting Features: ", progressbar.Percentage(), " ", progressbar.Bar(), " ", progressbar.ETA()]
pbar = progressbar.ProgressBar(maxval=len(imagePaths), widgets=widgets).start()

# loop over the images in patches
for i in np.arange(0, len(imagePaths), bs):
    # extract the batch of images and labels, then initialize the
    # list of actual images that will be passed through the network
    # for feature extraction
    batchPaths = imagePaths[i:i + bs]
    batchLabels = labels[i:i + bs]
    batchImages = []

    # loop over the images and labels in the current batch
    for (j, imagePath) in enumerate(batchPaths):
        # load the input image using the Keras helper utility
        # while ensuring the image is resized to 224x224 pixels
        image = load_img(imagePath, target_size=(224, 224))
        image = img_to_array(image)

        # preprocess the image by (1) expanding the dimensions and
        # (2) subtracting the mean RGB pixel intensity from the
        # ImageNet dataset
        image = np.expand_dims(image, axis=0)
        image = imagenet_utils.preprocess_input(image)

        # add the image to the batch
        batchImages.append(image)

    # pass the images through the network and use the outputs as
    # our actual features
    batchImages = np.vstack(batchImages)
    features = model.predict(batchImages, batch_size=bs)

    # reshape the features so that each image is represented by
    # a flattened feature vector of the `MaxPooling2D` outputs
    features = features.reshape((features.shape[0], 2048))

    # add the features and labels to our HDF5 dataset
    dataset.add(features, batchLabels)
    pbar.update(i)

# close the dataset
dataset.close()
pbar.finish()
