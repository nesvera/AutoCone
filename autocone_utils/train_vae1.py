import numpy as np
from glob import glob
import getpass
import os
import cv2
import random

from tensorflow.python import keras
from tensorflow.python.keras.layers import (
    Input, 
    Conv2D, 
    Conv2DTranspose, 
    Lambda, 
    Reshape, 
    Flatten, 
    Dense,
    MaxPooling2D,
    UpSampling2D,
)
from tensorflow.python.keras.models import Model
from tensorflow.python.keras import backend as K
from keras.callbacks import EarlyStopping
from tensorflow.python.keras.optimizers import Adam

class VAE():

    input_dim = (240, 320, 1)
    z_dim = 25

    dense_size = 32

    # number of images load of the memory to train
    minibatch_size = 500

    # number of times of loading a minibatch and train
    iterations = 500

    epochs = 1
    batch_size = 32

    # Save weights after some train iterations
    trains_btw_saves = 10

    def __init__(self):
        
        self.models = self.build_model3()
        self.model = self.models[0]
        self.encoder = self.models[1]
        self.decoder = self.models[2]

    def build_model(self):
        vae_input = Input( shape=self.input_dim)
        #print("vae_input shape " + str(vae_input.shape))

        vae_c1 = Conv2D( filters=32, kernel_size=4, strides=2, activation='relu')(vae_input)
        vae_c2 = Conv2D( filters=64, kernel_size=4, strides=2, activation='relu')(vae_c1)
        vae_c3 = Conv2D( filters=64, kernel_size=4, strides=2, activation='relu')(vae_c2)
        vae_c4 = Conv2D( filters=128, kernel_size=4, strides=2, activation='relu')(vae_c3)

        #print("vae_c1 shape " + str(vae_c1.shape))
        #print("vae_c2 shape " + str(vae_c2.shape))
        #print("vae_c3 shape " + str(vae_c3.shape))
        #print("vae_c4 shape " + str(vae_c4.shape))

        vae_z_in = Flatten()(vae_c4)
        #print("vae_z_in shape " + str(vae_z_in.shape))

        vae_z_mean = Dense(self.z_dim)(vae_z_in)
        vae_z_log_var = Dense(self.z_dim)(vae_z_in)
        #print("vae_z_mean shape " + str(vae_z_mean.shape))
        #print("vae_z_log_var shape " + str(vae_z_log_var.shape))

        vae_z = Lambda(self.sampling)([vae_z_mean, vae_z_log_var])
        vae_z_input = Input( shape=(self.z_dim,))
        print("vae_z shape " + str(vae_z.shape))
        #print("vae_z_input shape " + str(vae_z_input.shape))

        vae_dense = Dense(1024)
        vae_dense_model = vae_dense(vae_z)
        #print("vae_dense_model shape " + str(vae_dense_model.shape))

        vae_z_out = Reshape((1,1,self.dense_size))
        vae_z_out_model = vae_z_out(vae_dense_model)
        #print("vae_z_out_model shape " + str(vae_z_out_model.shape))

        vae_d1 = Conv2DTranspose( filters=64, kernel_size=(3, 4), strides=2, activation='relu')
        vae_d2 = Conv2DTranspose( filters=64, kernel_size=(9, 11), strides=3, activation='relu')
        vae_d3 = Conv2DTranspose( filters=32, kernel_size=(4, 4), strides=4, activation='relu')
        vae_d4 = Conv2DTranspose( filters=1, kernel_size=(4, 4), strides=4, activation='sigmoid')

        vae_d1_model = vae_d1(vae_z_out_model)
        vae_d2_model = vae_d2(vae_d1_model)
        vae_d3_model = vae_d3(vae_d2_model)
        vae_d4_model = vae_d4(vae_d3_model)
        #print("vae_d1_model shape " + str(vae_d1_model.shape))
        #print("vae_d2_model shape " + str(vae_d2_model.shape))
        #print("vae_d3_model shape " + str(vae_d3_model.shape))
        #print("vae_d4_model shape " + str(vae_d4_model.shape))

        vae_dense_decoder = vae_dense(vae_z_input)
        vae_z_out_decoder = vae_z_out(vae_dense_decoder)
        #print("vae_z_out_decoder shape " + str(vae_z_out_decoder.shape))

        vae_d1_decoder = vae_d1(vae_z_out_decoder)
        vae_d2_decoder = vae_d2(vae_d1_decoder)
        vae_d3_decoder = vae_d3(vae_d2_decoder)
        vae_d4_decoder = vae_d4(vae_d3_decoder)
        #print("vae_d1_decoder shape " + str(vae_d1_decoder.shape))
        #print("vae_d2_decoder shape " + str(vae_d2_decoder.shape))
        #print("vae_d3_decoder shape " + str(vae_d3_decoder.shape))
        #print("vae_d4_decoder shape " + str(vae_d4_decoder.shape))

        # Models
        vae = Model(vae_input, vae_d4_model)
        vae_encoder = Model(vae_input, vae_z)
        vae_decoder = Model(vae_z_input, vae_d4_decoder)

        def vae_r_loss(y_true, y_pred):

            y_true_flat = K.flatten(y_true)
            y_pred_flat = K.flatten(y_pred)

            return 10 * K.mean(K.square(y_true_flat - y_pred_flat), axis = -1)

        def vae_kl_loss(y_true, y_pred):
            return - 0.5 * K.mean(1 + vae_z_log_var - K.square(vae_z_mean) - K.exp(vae_z_log_var), axis = -1)

        def vae_loss(y_true, y_pred):
            return vae_r_loss(y_true, y_pred) + vae_kl_loss(y_true, y_pred)
            
        vae.compile(optimizer='rmsprop', loss = vae_loss,  metrics = [vae_r_loss, vae_kl_loss])
        vae.summary()

        return (vae, vae_encoder, vae_decoder)

    def build_model2(self):
        vae_input = Input( shape=self.input_dim)
        #print("vae_input shape " + str(vae_input.shape))

        vae_c1 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_input)
        vae_m1 = MaxPooling2D((2, 2), padding='same')(vae_c1)
        vae_c2 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m1)
        vae_m2 = MaxPooling2D((2, 2), padding='same')(vae_c2)
        vae_c3 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m2)
        vae_m3 = MaxPooling2D((2, 2), padding='same')(vae_c3)
        vae_c4 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m3)
        vae_m4 = MaxPooling2D((2, 2), padding='same')(vae_c4)
        vae_c5 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m4)
        vae_m5 = MaxPooling2D((2, 2), padding='same')(vae_c5)
        vae_c6 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m5)
        vae_m6 = MaxPooling2D((2, 2), padding='same')(vae_c6)

        print("vae_c1 shape " + str(vae_c1.shape))
        print("vae_c2 shape " + str(vae_c2.shape))
        print("vae_c3 shape " + str(vae_c3.shape))
        print("vae_c4 shape " + str(vae_c4.shape))
        # print("vae_c5 shape " + str(vae_c5.shape))
        print("vae_m1 shape " + str(vae_m1.shape))
        print("vae_m2 shape " + str(vae_m2.shape))
        print("vae_m3 shape " + str(vae_m3.shape))
        print("vae_m4 shape " + str(vae_m4.shape))
        # print("vae_m5 shape " + str(vae_m5.shape))

        vae_z_in = Flatten()(vae_m6)
        print("vae_z_in shape " + str(vae_z_in.shape))

        vae_z_mean = Dense(self.z_dim)(vae_z_in)
        vae_z_log_var = Dense(self.z_dim)(vae_z_in)
        #print("vae_z_mean shape " + str(vae_z_mean.shape))
        #print("vae_z_log_var shape " + str(vae_z_log_var.shape))

        vae_z = Lambda(self.sampling)([vae_z_mean, vae_z_log_var])
        vae_z_input = Input( shape=(self.z_dim,))
        #print("vae_z shape " + str(vae_z.shape))
        #print("vae_z_input shape " + str(vae_z_input.shape))

        # vae_dense = Dense(36, activation='relu ')
        # vae_dense_model = vae_dense(vae_z)
        # print("vae_dense_model shape " + str(vae_dense_model.shape))

        vae_z_out = Reshape((4, 4, 1))
        vae_z_out_model = vae_z_out(vae_z)
        #print("vae_z_out_model shape " + str(vae_z_out_model.shape))

        #vae_d1 = Conv2D( filters=8, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u1 = UpSampling2D((5,5))
        vae_d2 = Conv2D( filters=8, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u2 = UpSampling2D((3,2))
        vae_d3 = Conv2D( filters=8, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u3 = UpSampling2D((2,4))
        vae_d4 = Conv2D( filters=8, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u4 = UpSampling2D((2,2))
        vae_d5 = Conv2D( filters=1, kernel_size=(3, 3), padding='same', activation='sigmoid')

        # vae_d1_model = vae_d1(vae_z_out_model)
        vae_u1_model = vae_u1(vae_z_out_model)
        vae_d2_model = vae_d2(vae_u1_model)
        vae_u2_model = vae_u2(vae_d2_model)
        vae_d3_model = vae_d3(vae_u2_model)
        vae_u3_model = vae_u3(vae_d3_model)
        vae_d4_model = vae_d4(vae_u3_model)
        vae_u4_model = vae_u4(vae_d4_model)
        vae_d5_model = vae_d5(vae_u4_model)
        #print("vae_d1_model shape " + str(vae_d1_model.shape))
        #print("vae_u1_model shape " + str(vae_u1_model.shape))
        #print("vae_d2_model shape " + str(vae_d2_model.shape))
        #print("vae_u2_model shape " + str(vae_u2_model.shape))
        #print("vae_d3_model shape " + str(vae_d3_model.shape))
        #print("vae_u3_model shape " + str(vae_u3_model.shape))
        #print("vae_d4_model shape " + str(vae_d4_model.shape))
        #print("vae_u4_model shape " + str(vae_u4_model.shape))
        #print("vae_d5_model shape " + str(vae_d5_model.shape))

        #vae_dense_decoder = vae_dense(vae_z_input)
        vae_z_out_decoder = vae_z_out(vae_z_input)
        #print("vae_z_out_decoder shape " + str(vae_z_out_decoder.shape))

        #vae_d1_decoder = vae_d1(vae_z_out_decoder)
        vae_u1_decoder = vae_u1(vae_z_out_decoder)
        vae_d2_decoder = vae_d2(vae_u1_decoder)
        vae_u2_decoder = vae_u2(vae_d2_decoder)
        vae_d3_decoder = vae_d3(vae_u2_decoder)
        vae_u3_decoder = vae_u3(vae_d3_decoder)
        vae_d4_decoder = vae_d4(vae_u3_decoder)
        vae_u4_decoder = vae_u4(vae_d4_decoder)
        vae_d5_decoder = vae_d5(vae_u4_decoder)
        #print("vae_d1_decoder shape " + str(vae_d1_decoder.shape))
        #print("vae_d2_decoder shape " + str(vae_d2_decoder.shape))
        #print("vae_d3_decoder shape " + str(vae_d3_decoder.shape))
        #print("vae_d4_decoder shape " + str(vae_d4_decoder.shape))
        # print("vae_d5_decoder shape " + str(vae_d5_decoder.shape))

        # Models
        vae = Model(vae_input, vae_d5_model)
        vae_encoder = Model(vae_input, vae_z)
        vae_decoder = Model(vae_z_input, vae_d5_decoder)

        def vae_r_loss(y_true, y_pred):

            y_true_flat = K.flatten(y_true)
            y_pred_flat = K.flatten(y_pred)

            return 10 * K.mean(K.square(y_true_flat - y_pred_flat), axis = -1)

        def vae_kl_loss(y_true, y_pred):
            return - 0.5 * K.mean(1 + vae_z_log_var - K.square(vae_z_mean) - K.exp(vae_z_log_var), axis = -1)

        def vae_loss(y_true, y_pred):
            return vae_r_loss(y_true, y_pred) + vae_kl_loss(y_true, y_pred)
            
        vae.compile(optimizer='rmsprop', loss = vae_loss,  metrics = [vae_r_loss, vae_kl_loss])
        vae.summary()

        return (vae, vae_encoder, vae_decoder)

    def build_model3(self):
        vae_input = Input( shape=self.input_dim)
        #print("vae_input shape " + str(vae_input.shape))

        vae_c1 = Conv2D( filters=16, kernel_size=3, padding='same', activation='relu')(vae_input)
        vae_m1 = MaxPooling2D((2, 2), padding='same')(vae_c1)
        vae_c2 = Conv2D( filters=16, kernel_size=3, padding='same', activation='relu')(vae_m1)
        vae_m2 = MaxPooling2D((2, 2), padding='same')(vae_c2)
        vae_c3 = Conv2D( filters=16, kernel_size=3, padding='same', activation='relu')(vae_m2)
        vae_m3 = MaxPooling2D((2, 2), padding='same')(vae_c3)
        vae_c4 = Conv2D( filters=16, kernel_size=3, padding='same', activation='relu')(vae_m3)
        vae_m4 = MaxPooling2D((2, 2), padding='same')(vae_c4)
        vae_c5 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m4)
        vae_m5 = MaxPooling2D((2, 2), padding='same')(vae_c5)
        vae_c6 = Conv2D( filters=8, kernel_size=3, padding='same', activation='relu')(vae_m5)
        vae_m6 = MaxPooling2D((2, 2), padding='same')(vae_c6)

        #print("vae_c1 shape " + str(vae_c1.shape))
        #print("vae_c2 shape " + str(vae_c2.shape))
        #print("vae_c3 shape " + str(vae_c3.shape))
        #print("vae_c4 shape " + str(vae_c4.shape))
        # print("vae_c5 shape " + str(vae_c5.shape))
        #print("vae_m1 shape " + str(vae_m1.shape))
        #print("vae_m2 shape " + str(vae_m2.shape))
        #print("vae_m3 shape " + str(vae_m3.shape))
        #print("vae_m4 shape " + str(vae_m4.shape))
        #print("vae_m5 shape " + str(vae_m5.shape))
        #print("vae_m6 shape " + str(vae_m6.shape))

        vae_z_in = Flatten()(vae_m6)
        print("vae_z_in shape " + str(vae_z_in.shape))

        vae_z_mean = Dense(self.z_dim)(vae_z_in)
        vae_z_log_var = Dense(self.z_dim)(vae_z_in)
        #print("vae_z_mean shape " + str(vae_z_mean.shape))
        #print("vae_z_log_var shape " + str(vae_z_log_var.shape))

        vae_z = Lambda(self.sampling)([vae_z_mean, vae_z_log_var])
        vae_z_input = Input( shape=(self.z_dim,))
        #print("vae_z shape " + str(vae_z.shape))
        #print("vae_z_input shape " + str(vae_z_input.shape))

        vae_z_out = Reshape((5, 5, 1))
        vae_z_out_model = vae_z_out(vae_z)
        #print("vae_z_out_model shape " + str(vae_z_out_model.shape))


        #vae_d1 = Conv2D( filters=8, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u1 = UpSampling2D((3,4))
        vae_d2 = Conv2D( filters=16, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u2 = UpSampling2D((2,2))
        vae_d3 = Conv2D( filters=16, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u3 = UpSampling2D((2,2))
        vae_d4 = Conv2D( filters=8, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u4 = UpSampling2D((2,2))
        vae_d5 = Conv2D( filters=4, kernel_size=(3, 3), padding='same', activation='relu')
        vae_u5 = UpSampling2D((2,2))
        vae_d6 = Conv2D( filters=1, kernel_size=(3, 3), padding='same', activation='sigmoid')

        # vae_d1_model = vae_d1(vae_z_out_model)
        vae_u1_model = vae_u1(vae_z_out_model)
        vae_d2_model = vae_d2(vae_u1_model)
        vae_u2_model = vae_u2(vae_d2_model)
        vae_d3_model = vae_d3(vae_u2_model)
        vae_u3_model = vae_u3(vae_d3_model)
        vae_d4_model = vae_d4(vae_u3_model)
        vae_u4_model = vae_u4(vae_d4_model)
        vae_d5_model = vae_d5(vae_u4_model)
        vae_u5_model = vae_u5(vae_d5_model)
        vae_d6_model = vae_d6(vae_u5_model)
        #print("vae_d1_model shape " + str(vae_d1_model.shape))
        #print("vae_u1_model shape " + str(vae_u1_model.shape))
        #print("vae_d2_model shape " + str(vae_d2_model.shape))
        #print("vae_u2_model shape " + str(vae_u2_model.shape))
        #print("vae_d3_model shape " + str(vae_d3_model.shape))
        #print("vae_u3_model shape " + str(vae_u3_model.shape))
        #print("vae_d4_model shape " + str(vae_d4_model.shape))
        #print("vae_u4_model shape " + str(vae_u4_model.shape))
        #print("vae_d5_model shape " + str(vae_d5_model.shape))

        #240 120 60 30 15
        #320 160 80 40 20

        vae_dense_decoder = vae_z_input
        vae_z_out_decoder = vae_z_out(vae_dense_decoder)

        #vae_d1_decoder = vae_d1(vae_z_out_decoder)
        vae_u1_decoder = vae_u1(vae_z_out_decoder)
        vae_d2_decoder = vae_d2(vae_u1_decoder)
        vae_u2_decoder = vae_u2(vae_d2_decoder)
        vae_d3_decoder = vae_d3(vae_u2_decoder)
        vae_u3_decoder = vae_u3(vae_d3_decoder)
        vae_d4_decoder = vae_d4(vae_u3_decoder)
        vae_u4_decoder = vae_u4(vae_d4_decoder)
        vae_d5_decoder = vae_d5(vae_u4_decoder)
        vae_u5_decoder = vae_u5(vae_d5_decoder)
        vae_d6_decoder = vae_d6(vae_u5_decoder)
        print("vae_d1_decoder shape " + str(vae_u1_decoder.shape))
        print("vae_d2_decoder shape " + str(vae_d2_decoder.shape))
        print("vae_d3_decoder shape " + str(vae_d3_decoder.shape))
        print("vae_d4_decoder shape " + str(vae_d4_decoder.shape))
        print("vae_d5_decoder shape " + str(vae_d5_decoder.shape))

        # Models
        vae = Model(vae_input, vae_d6_model)
        vae_encoder = Model(vae_input, vae_z)
        vae_decoder = Model(vae_z_input, vae_d6_decoder)

        def vae_r_loss(y_true, y_pred):

            y_true_flat = K.flatten(y_true)
            y_pred_flat = K.flatten(y_pred)

            return 10 * K.mean(K.square(y_true_flat - y_pred_flat), axis = -1)

        def vae_kl_loss(y_true, y_pred):
            return - 0.5 * K.mean(1 + vae_z_log_var - K.square(vae_z_mean) - K.exp(vae_z_log_var), axis = -1)

        def vae_loss(y_true, y_pred):
            return vae_r_loss(y_true, y_pred) + vae_kl_loss(y_true, y_pred)
            
        #vae.compile(optimizer='rmsprop', loss = vae_loss,  metrics = [vae_r_loss, vae_kl_loss])
        vae.compile(optimizer=Adam(lr=0.005), loss = vae_loss,  metrics = [vae_r_loss, vae_kl_loss])
        vae.summary()

        return (vae, vae_encoder, vae_decoder)

    def sampling(self, args):
        z_mean, z_log_var = args
        epsilon = K.random_normal( shape=(K.shape(z_mean)[0], self.z_dim), mean=0., stddev=1.)
        return ( z_mean + K.exp(z_log_var/2.)*epsilon)

    def save_weights(self, filepath):
        self.model.save_weights(filepath)

    def load_weights(self, filepath):
        self.model.load_weights(filepath)

    def train(self):
        username = getpass.getuser()
        vae_dataset_folder = '/home/' + username + '/Documents/autocone_vae_dataset/'
        vae_weights_folder = '/home/' + username + '/Documents/autocone_vae_weights/'

        # get all images files inside the folder
        dataset = glob(vae_dataset_folder + "*.jpg")
        dataset_total = len(dataset)

        minibatch_begin = 0
        minibatch_end = self.minibatch_size

        n_trains = 0

        i = 0
        while i < self.iterations:

            print("Iteration " + str(i) + " of " + str(self.iterations))
            print("Data from " + str(minibatch_begin) + " to " + str(minibatch_end) + " of Total: " + str(dataset_total))
            print("")

            # load minibatch
            minibatch = dataset[minibatch_begin: minibatch_end]

            data = np.zeros((self.minibatch_size, self.input_dim[0], self.input_dim[1], self.input_dim[2]))
            for j, img_file in enumerate(minibatch):
                img = cv2.imread(img_file, 0)
                img = img.astype('float32')/255.
                #img = np.reshape(img, (1, img.shape[0], img.shape[1], 1))
                
                data[j, :, :, 0] = img

            #for f in range(len(minibatch)):
            #    imagem = data[f, :, :, 0]
            #    cv2.imshow('image', imagem)
            #    cv2.waitKey(0)

            #self.model.fit( x=data, y=data, shuffle=True, epochs=self.epochs, batch_size=self.batch_size)

            earlystop = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=5, verbose=1, mode='auto')
            callbacks_list = [earlystop]

            self.model.fit( x=data, y=data,
                    shuffle=True,
                    epochs=self.epochs,
                    batch_size=self.batch_size,
                    callbacks=callbacks_list)

            # save weights after some trains sections
            if n_trains % self.trains_btw_saves == 0:
                filename = vae_weights_folder + str(i) + "_" + str(minibatch_begin) + "_" + str(minibatch_end) + ".h5"
                print("Saving " + filename)
                self.save_weights(filename)

            n_trains += 1

            # increase indexes of dataset
            minibatch_begin += self.minibatch_size
            minibatch_end += self.minibatch_size

            # after pass over all dataset, go for other iteration
            if minibatch_begin >= len(dataset):
                minibatch_begin = 0
                minibatch_end = self.minibatch_size

                i += 1

            elif minibatch_end >= len(dataset):
                minibatch_end = len(dataset)

    def generate_image(self, z_input):
        img = self.decoder.predict(z_input)

        return img

    def encode_image(self, data):
        
        z = self.encoder.predict(data)

        return z


if __name__ == "__main__":

    username = getpass.getuser()
    vae_weight = '/home/' + username + '/Documents/autocone_vae_weights/' + "4_71000_71500.h5"

    vae = VAE()
    #vae.train()

    vae.load_weights(vae_weight)

    #vae.train()

    vae_dataset_folder = '/home/' + username + '/Documents/autocone_vae_dataset/'

    # get all images files inside the folder
    dataset = glob(vae_dataset_folder + "*.jpg")

    
    while False:
        img_file = random.choice(dataset)
        img = cv2.imread(img_file, 0)
        print(img)

        img = img.astype('float32')/255.
        print(img)

        cv2.imshow('input', img)

        img = np.reshape(img, (1, img.shape[0], img.shape[1], 1))                

        z = vae.encode_image(img)
        print(z)

        img_out = vae.generate_image(z)
        img_out = np.reshape(img_out, (img_out.shape[1], img_out.shape[2]))

        cv2.imshow('output', img_out)
        cv2.waitKey(0)
    
    z = np.zeros((1, 25))

    while True:

        for i in range(25):
            z[0, i] = random.gauss(0, 10)
            #z[0, i] = random.uniform(-2, 2)

        print(z)
       
        img_out = vae.generate_image(z)


        img_out = np.reshape(img_out, (img_out.shape[1], img_out.shape[2]))
        
        cv2.imshow('carai', img_out)
        cv2.waitKey(0)
    
