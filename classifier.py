import os
import numpy as np
from datetime import datetime
import tensorflow as tf
from tensorflow.keras.layers import Dense, Flatten, Conv1D, Conv2D, Conv3D, RNN, GRUCell, StackedRNNCells, ReLU, \
    Reshape, BatchNormalization, ReLU, Dropout, MaxPooling1D, Dropout, TimeDistributed, LSTM, ConvLSTM2D
from sklearn.metrics import matthews_corrcoef, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

from data_loader import load_data


class CNN_LSTM_(tf.keras.models.Sequential):

    def __init__(self):
        super().__init__()

    def create_model(self):
        self.add(TimeDistributed(Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=(None, 4, 25, 8))))
        self.add(TimeDistributed(Conv1D(filters=64, kernel_size=3, activation='relu')))
        self.add(TimeDistributed(Dropout(0.5)))
        self.add(TimeDistributed(MaxPooling1D(pool_size=2)))
        self.add(TimeDistributed(Flatten()))
        self.add(LSTM(100))
        self.add(Dropout(0.5))
        self.add(Dense(100, activation='relu'))
        self.add(Dense(1, activation='sigmoid'))


class DeepSense(tf.keras.Model):

    def __init__(self, fft_window, image_width):
        super(DeepSense, self).__init__()

        self.acc_conv1 = Conv3D(64, kernel_size=(3, 3, 3), activation=None, padding='valid',
                                input_shape=(None, fft_window, image_width, 3, 2))
        self.acc_batch_norm1 = BatchNormalization()
        self.acc_act1 = ReLU()
        self.acc_dropout1 = Dropout(0.5)

        self.acc_conv2 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='same')
        self.acc_batch_norm2 = BatchNormalization()
        self.acc_act2 = ReLU()
        self.acc_dropout2 = Dropout(0.5)

        self.acc_conv3 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='same')
        self.acc_batch_norm3 = BatchNormalization()
        self.acc_act3 = ReLU()

        self.gyro_conv1 = Conv3D(64, kernel_size=(3, 3, 3), activation=None, padding='valid',
                                 input_shape=(None, fft_window, image_width, 3, 2))
        self.gyro_batch_norm1 = BatchNormalization()
        self.gyro_act1 = ReLU()
        self.gyro_dropout1 = Dropout(0.5)

        self.gyro_conv2 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='same')
        self.gyro_batch_norm2 = BatchNormalization()
        self.gyro_act2 = ReLU()
        self.gyro_dropout2 = Dropout(0.5)

        self.gyro_conv3 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='same')
        self.gyro_batch_norm3 = BatchNormalization()
        self.gyro_act3 = ReLU()

        self.sensor_dropout = Dropout(0.5)

        self.sensor_conv1 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='SAME')
        self.sensor_batch_norm1 = BatchNormalization()
        self.sensor_act1 = ReLU()
        self.sensor_dropout1 = Dropout(0.5)

        self.sensor_conv2 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='SAME')
        self.sensor_batch_norm2 = BatchNormalization()
        self.sensor_act2 = ReLU()
        self.sensor_dropout2 = Dropout(0.5)

        self.sensor_conv3 = Conv3D(64, kernel_size=(3, 3, 1), activation=None, padding='SAME')
        self.sensor_batch_norm3 = BatchNormalization()
        self.sensor_act3 = ReLU()
        self.sensor_dropout3 = Dropout(0.5)

        self.sensor_reshape = Reshape((18, 6 * 2 * 64))

        self.sensor_gru1 = GRUCell(120, activation=None)
        self.sensor_gru2 = GRUCell(120, activation=None)
        self.sensor_stacked_rnn = RNN(StackedRNNCells([self.sensor_gru1, self.sensor_gru2]), return_sequences=True)

        self.sensor_gru1_dropout = GRUCell(120, dropout=0.5, activation=None)
        self.sensor_gru2_dropout = GRUCell(120, dropout=0.5, activation=None)
        self.sensor_stacked_rnn_dropout = RNN(StackedRNNCells([self.sensor_gru1_dropout, self.sensor_gru2_dropout]),
                                              return_sequences=True)

        self.fc = Dense(1, activation='sigmoid')

    def call(self, x, training):
        # split sensors
        acc, gyro, gps = tf.split(x, num_or_size_splits=3, axis=3)

        # remove incidents
        gps = gps[:, :, :, :2]

        # split real and imaginary part of complex accelerometer data
        acc_real = tf.math.real(acc)
        acc_imag = tf.math.imag(acc)
        acc = tf.stack((acc_real, acc_imag), axis=4)

        # split real and imaginary part of complex gyrosensor data
        gyro_real = tf.math.real(gyro)
        gyro_imag = tf.math.imag(gyro)
        gyro = tf.stack((gyro_real, gyro_imag), axis=4)

        # get real part of complex gps data
        gps = tf.math.real(gps)

        acc = self.acc_conv1(acc)
        acc = self.acc_batch_norm1(acc)
        acc = self.acc_act1(acc)
        acc = self.acc_dropout1(acc) if training else acc

        acc = self.acc_conv2(acc)
        acc = self.acc_batch_norm2(acc)
        acc = self.acc_act2(acc)
        acc = self.acc_dropout2(acc) if training else acc

        acc = self.acc_conv3(acc)
        acc = self.acc_batch_norm3(acc)
        acc = self.acc_act3(acc)

        gyro = self.gyro_conv1(gyro)
        gyro = self.gyro_batch_norm1(gyro)
        gyro = self.gyro_act1(gyro)
        gyro = self.gyro_dropout1(gyro) if training else gyro

        gyro = self.gyro_conv2(gyro)
        gyro = self.gyro_batch_norm2(gyro)
        gyro = self.gyro_act2(gyro)
        gyro = self.gyro_dropout2(gyro) if training else gyro

        gyro = self.gyro_conv3(gyro)
        gyro = self.gyro_batch_norm3(gyro)
        gyro = self.gyro_act3(gyro)

        sensor = tf.concat([acc[:, :, :, :, :], gyro[:, :, :, :, :]], 3)

        sensor = self.sensor_dropout(sensor)

        sensor = self.sensor_conv1(sensor)
        sensor = self.sensor_batch_norm1(sensor)
        sensor = self.sensor_act1(sensor)
        sensor = self.sensor_dropout1(sensor) if training else sensor

        sensor = self.sensor_conv2(sensor)
        sensor = self.sensor_batch_norm2(sensor)
        sensor = self.sensor_act2(sensor)
        sensor = self.sensor_dropout2(sensor) if training else sensor

        sensor = self.sensor_conv3(sensor)
        sensor = self.sensor_batch_norm3(sensor)
        sensor = self.sensor_act3(sensor)
        sensor = self.sensor_dropout3(sensor) if training else sensor

        sensor = tf.transpose(sensor, perm=(0, 2, 1, 3, 4))
        sensor = self.sensor_reshape(sensor)

        sensor = self.sensor_stacked_rnn_dropout(sensor) if training else self.sensor_stacked_rnn(sensor)

        sensor = tf.math.reduce_mean(sensor, axis=1, keepdims=False)

        sensor = self.fc(sensor)

        return sensor


def train(train_ds, val_ds, test_ds, class_weight, num_epochs=10, patience=1, checkpoint_dir='checkpoints/cnn/training',
          fourier=True, fft_window=8, image_width=20):
    if fourier:
        model = DeepSense(fft_window, image_width)

    else:
        model = CNN_LSTM_()
        model.create_model()

    optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001)
    auc = tf.keras.metrics.AUC(from_logits=False)
    model.compile(optimizer=optimizer, loss=tf.keras.losses.BinaryCrossentropy(from_logits=False),
                  metrics=['accuracy', auc])

    latest = tf.train.latest_checkpoint(os.path.dirname(checkpoint_dir))
    try:
        model.load_weights(latest)
    except:
        print('There is no existing checkpoint')

    # Create a callback that saves the model's weights
    cp_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_dir,
        monitor='val_auc',
        verbose=1,
        save_best_only=True,
        mode='max',
        save_weights_only=True,
        save_freq='epoch')

    # Create a callback for early stopping
    es_callback = tf.keras.callbacks.EarlyStopping(
        monitor='val_accuracy',
        patience=patience,
        verbose=1)

    # Define the Keras TensorBoard callback.
    tb_logdir = 'tb_logs/fit/' + datetime.now().strftime('%Y%m%d-%H%M%S')
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=tb_logdir, histogram_freq=1)

    model.fit(train_ds, validation_data=val_ds, epochs=num_epochs,
              callbacks=[cp_callback, es_callback, tensorboard_callback], class_weight=class_weight)

    print()
    print('Model evaluation on train set after training:')
    model.evaluate(train_ds)

    latest = tf.train.latest_checkpoint(os.path.dirname(checkpoint_dir))
    model.load_weights(latest)

    print('Model evaluation on train set:')
    model.evaluate(train_ds)
    print('Model evaluation on val set:')
    model.evaluate(val_ds)
    print('Model evaluation on test set:')
    model.evaluate(test_ds)

    y_pred = model.predict(test_ds)

    y_true = np.concatenate([y for x, y in test_ds], axis=0)

    y_pred = np.round(y_pred)[:, 0]

    print('Confusion matrix:')
    print(confusion_matrix(y_true, y_pred))
    print('F1 score:')
    print(f1_score(y_true, y_pred))
    print('Precision score:')
    print(precision_score(y_true, y_pred))
    print('Recall score:')
    print(recall_score(y_true, y_pred))
    print('Phi score:')
    print(matthews_corrcoef(y_true, y_pred))


if __name__ == '__main__':
    dir = '../Ride_Data'
    checkpoint_dir = 'checkpoints/cnn/training'
    target_region = 'Berlin'
    bucket_size = 100
    batch_size = 128
    num_epochs = 100
    patience = 25
    fourier = True
    fft_window = 8
    image_width = 20

    train_ds, val_ds, test_ds, class_weight = load_data(dir, target_region, batch_size, fourier)
    train(train_ds, val_ds, test_ds, class_weight, num_epochs, patience, checkpoint_dir, fourier, fft_window,
          image_width)
