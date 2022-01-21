import os
import numpy as np
from datetime import datetime
import tensorflow as tf
from tensorflow.keras.layers import Reshape
from sklearn.metrics import confusion_matrix

from data_loader import load_data
from metrics import TSS
from tensorflow_addons.layers import ESN


class ESN_Model(tf.keras.models.Sequential):

    def __init__(self):
        super().__init__()

    def create_model(self):
        self.add(Reshape((100, 8)))
        self.add(ESN(100))
        self.add(tf.keras.layers.Dense(1, activation='sigmoid'))


def train(train_ds, val_ds, test_ds, class_weight, num_epochs=10, patience=1,
          checkpoint_dir='checkpoints/esn/training'):
    model = ESN_Model()
    model.create_model()

    optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001)

    model.compile(optimizer=optimizer, loss=tf.keras.losses.BinaryCrossentropy(from_logits=False),
                  metrics=['accuracy', tf.keras.metrics.TrueNegatives(name='tn'),
                           tf.keras.metrics.FalsePositives(name='fp'),
                           tf.keras.metrics.FalseNegatives(name='fn'), tf.keras.metrics.TruePositives(name='tp'),
                           tf.keras.metrics.AUC(curve='roc', from_logits=False, name='aucroc'),
                           tf.keras.metrics.AUC(curve='PR', from_logits=False, name='aucpr'),
                           TSS(), tf.keras.metrics.SensitivityAtSpecificity(0.96, name='sas')
                           ])

    latest = tf.train.latest_checkpoint(os.path.dirname(checkpoint_dir))
    try:
        model.load_weights(latest)
    except:
        print('There is no existing checkpoint')

    # Create a callback that saves the model's weights
    cp_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_dir,
        monitor='val_aucroc',
        verbose=1,
        save_best_only=True,
        mode='max',
        save_weights_only=True,
        save_freq='epoch')

    # Create a callback for early stopping
    es_callback = tf.keras.callbacks.EarlyStopping(
        monitor='val_aucroc',
        patience=patience,
        verbose=1,
        mode='max',
        restore_best_weights=True)

    # Define the Keras TensorBoard callback.
    tb_logdir = 'tb_logs/fit/' + datetime.now().strftime('%Y%m%d-%H%M%S')
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=tb_logdir, histogram_freq=1)

    model.fit(train_ds, validation_data=val_ds, epochs=num_epochs,
              callbacks=[es_callback, cp_callback, tensorboard_callback], class_weight=class_weight)

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

    model.summary()


if __name__ == '__main__':
    dir = 'Ride_Data'
    checkpoint_dir = 'checkpoints/esn/training'
    target_region = 'Berlin'
    bucket_size = 100
    batch_size = 128
    in_memory_flag = True
    num_epochs = 100
    patience = 10
    window_size = 5
    slices = 20
    class_counts_file = os.path.join(dir, 'class_counts.csv')
    input_shape = (None, slices, window_size, 8)
    transpose_flag = True
    cache_dir = None

    train_ds, val_ds, test_ds, class_weight = load_data(dir, target_region, input_shape=input_shape,
                                                        batch_size=batch_size, in_memory_flag=in_memory_flag,
                                                        transpose_flag=transpose_flag,
                                                        class_counts_file=class_counts_file, cache_dir=cache_dir)

    train(train_ds, val_ds, test_ds, class_weight, num_epochs, patience, checkpoint_dir)
