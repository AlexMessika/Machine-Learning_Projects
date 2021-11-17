from __future__ import print_function
import keras
from keras.datasets import mnist
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D, AveragePooling2D, Input
from keras import backend as K
import pandas as pd
import numpy as np
from sklearn import utils
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.utils import class_weight
#from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from keras import regularizers
from keras.layers.core import *
from keras.models import Model
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import confusion_matrix
from keras.utils import np_utils
import tensorflow as tf
from keras.models import load_model
from keras.utils.vis_utils import plot_model
import pydot
import graphviz


pca_exp = pd.read_excel("data/PCA_EXP.xlsx", header=None)
pca_cnv = pd.read_excel("data/PCA_CNV.xlsx", header=None)
pca_mt = pd.read_excel("data/PCA_MT.xlsx", header=None)
clinical = pd.read_excel("data/Clinical.xlsx")
print(pca_cnv)
n = len(pca_exp)  # sample size: number of Pts
path_n = 146  # number of pathways
pc = 5  # number of PCs

# data creation-EXP
pca_exp = pca_exp.to_numpy()
exp_data = np.zeros((n, path_n, pc))
for i in range(n):
    for j in range(path_n):
        exp_data[i, j, :] = pca_exp[i, j * pc:(j + 1) * pc]

# data creation-CNV
pca_cnv = pca_cnv.to_numpy()
cnv_data = np.zeros((n, path_n, pc))
for i in range(n):
    for j in range(path_n):
        cnv_data[i, j, :] = pca_cnv[i, j * pc:(j + 1) * pc]

# data creation-MT
pca_mt = pca_mt.to_numpy()
mt_data = np.zeros((n, path_n, pc))
for i in range(n):
    for j in range(path_n):
        mt_data[i, j, :] = pca_mt[i, j * pc:(j + 1) * pc]

# data merge: mRNA expression, CNV, and MT with a specific number of PCs
no_pc = 2  # use the first 2PCs among 5 PCs
all_data = np.zeros((n, path_n, no_pc * 3))
for i in range(n):
        all_data[i, :, :] = np.concatenate((exp_data[i, :, 0:no_pc], cnv_data[i, :, 0:no_pc], mt_data[i, :, 0:no_pc]),axis=1)

clinical = clinical.to_numpy()
age = clinical[:, 4]
survival = clinical[:, 5]
os_months = clinical[:, 6]
idx0 = np.where((survival == 1) & (os_months <= 24))
idx1 = np.where(os_months > 24)

bio_data=clinical[:, 7:10]
all_data = all_data[:, :, :]

data_0 = all_data[idx0, :, :]
data_0 = data_0[0, :, :, :]
data_1 = all_data[idx1, :, :]
data_1 = data_1[0, :, :, :]

age_0 = age[idx0]
age_1 = age[idx1]

bio_data_0 = bio_data[idx0, : ]
bio_data_0 = bio_data_0[0, :, :]
bio_data_1 = bio_data[idx1,:]
bio_data_1 = bio_data_1[0, :, :]

outcomes_0 = np.zeros(len(idx0[0]))
outcomes_1 = np.ones(len(idx1[0]))

## data merge
age_r = np.concatenate((age_0, age_1))
data = np.concatenate((data_0, data_1))
outcomes = np.concatenate((outcomes_0, outcomes_1))
bio_data_r=np.concatenate((bio_data_0, bio_data_1))

## DEEP LEARNING
batch_size = 64
epochs = 30

num_classes = 2
num_runs = 30
k_fold = 5

# input image dimension
img_rows, img_cols = 146, 6

auc = []

all_observed = np.array([])
all_predicted = np.array([])

for i in range(num_runs):
    print(i)
    # 5-fold cross validation
    skf = StratifiedKFold(n_splits=5)

    observed = np.array([])
    predicted = np.array([])

    observed = np.array([])
    predicted = np.array([])

    for train1, test in skf.split(data,outcomes):
        skf1 = StratifiedKFold(n_splits=5)
        train_data=data[train1,:,:]
        train_outcomes=outcomes[train1]

        for train, validation in skf1.split(train_data, train_outcomes):
            break

        x_train = train_data[train, :, :]
        y_train = train_outcomes[train]

        x_validation = train_data[validation, :, :]
        y_validation = train_outcomes[validation]

        x_test = data[test, :, :]
        y_test = outcomes[test]

        # age
        age_r1=age_r[train1]
        age_train = age_r1[train]
        age_validation = age_r1[validation]
        age_test = age_r[test]

        # bio
        bio_data_r1 = bio_data_r[train1, :]
        bio_data_train = bio_data_r1[train,:]
        bio_data_validation = bio_data_r1[validation, :]
        bio_data_test = bio_data_r[test,:]

        cli_train=np.concatenate((np.matrix([age_train]).T, bio_data_train), axis=1)
        cli_validation = np.concatenate((np.matrix([age_validation]).T, bio_data_validation), axis=1)
        cli_test = np.concatenate((np.matrix([age_test]).T, bio_data_test), axis=1)

        x_train = x_train.reshape(x_train.shape[0], img_rows, img_cols, 1)  # rgb- add one more dimensionality
        x_validation = x_validation.reshape(x_validation.shape[0], img_rows, img_cols, 1)
        x_test = x_test.reshape(x_test.shape[0], img_rows, img_cols, 1)
        input_shape = (img_rows, img_cols, 1)

        x_train = x_train.astype('float32')
        x_validation = x_validation.astype('float32')
        x_test = x_test.astype('float32')

        print('x_train shape:', x_train.shape)
        print(x_train.shape[0], 'train samples')
        print(x_validation.shape[0], 'validation samples')
        print(x_test.shape[0], 'test samples')

        y_train = tf.keras.utils.to_categorical(y_train, num_classes)
        y_validation = tf.keras.utils.to_categorical(y_validation, num_classes)
        y_test = tf.keras.utils.to_categorical(y_test, num_classes)

        image_input = Input(shape=input_shape)
        other_data_input = Input(shape=(1,))

        # First convolution
        conv1 = Conv2D(32, kernel_size=(3, 3),
                       activation='relu', padding='same'
                       )(image_input)
        # Second Convolution
        conv2 = Conv2D(64, (3, 3), activation='relu', padding='same'
                       )(conv1)
        conv2 = MaxPooling2D(pool_size=(4, 2))(conv2)
        conv2 = Dropout(0.25)(conv2)
        first_part_output = Flatten()(conv2)

        merged_model = keras.layers.concatenate([first_part_output, other_data_input])
        merged_model = Dense(64, activation='relu')(merged_model)
        merged_model = Dropout(0.5)(merged_model)

        predictions = Dense(num_classes, activation='softmax')(merged_model)

        '''
        # Now create the model
        model = Model(inputs=[image_input, other_data_input], outputs=predictions)
        model.summary()
        layers = model.layers

        lr = 0.0001
        beta_1 = 0.9
        beta_2 = 0.999
        optimizer = Adam(lr=lr, beta_1=beta_1, beta_2=beta_2)

        model.compile(optimizer=optimizer, loss='binary_crossentropy',
                      metrics=['accuracy'])

        class_weighting = {0: 1, 1: 4.2}  # class weight
        model.fit([x_train, age_train], y_train,
                  batch_size=batch_size,
                  epochs=epochs,
                  verbose=1, class_weight=class_weighting,
                  validation_data=([x_validation, age_validation], [y_validation]))

        #save model
        model.save("path_CNN.h5")
        print("Saved model to disk")
        '''

        model = load_model('path_CNN.h5')
        tf.keras.utils.plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)


        score = model.predict([x_test, age_test], verbose=0)
        

        if len(observed) == 0:
            observed = y_test
            predicted = score
        else:
            observed = np.concatenate((observed, y_test))
            predicted = np.concatenate((predicted, score))

    auc.append(roc_auc_score(observed[:, 0], predicted[:, 0]))

    if len(all_observed) == 0:
        all_observed = observed[:, 0]
        all_predicted = predicted[:, 0]
    else:
        all_observed = np.concatenate((all_observed, observed[:, 0]))
        all_predicted = np.concatenate((all_predicted, predicted[:, 0]))

    print(auc)
print(auc)



pd.DataFrame(auc).to_csv("results.csv")