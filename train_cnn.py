import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.utils import to_categorical
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Load and preprocess data
(x_train, y_train), (x_test, y_test) = cifar10.load_data()
x_train = x_train.astype('float32') / 255.0
x_test = x_test.astype('float32') / 255.0

# Map CIFAR-10 to 2 classes: person (living entities), others (objects)
y_train_mapped = np.zeros_like(y_train)
y_test_mapped = np.zeros_like(y_test)
for i in range(len(y_train)):
    if y_train[i] in [2, 3, 4, 5, 6, 7]:  # bird, cat, deer, dog, frog, horse
        y_train_mapped[i] = 0  # person
    else:  # airplane, automobile, ship, truck
        y_train_mapped[i] = 1  # others
for i in range(len(y_test)):
    if y_test[i] in [2, 3, 4, 5, 6, 7]:
        y_test_mapped[i] = 0
    else:
        y_test_mapped[i] = 1
y_train_mapped = to_categorical(y_train_mapped, 2)
y_test_mapped = to_categorical(y_test_mapped, 2)

# Data augmentation
datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    fill_mode='nearest'
)
datagen.fit(x_train)

# Build and train model
model = models.Sequential([
    layers.Input(shape=(32, 32, 3)),
    layers.Conv2D(32, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(2, activation='softmax')  # 2 classes
])
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
model.fit(datagen.flow(x_train, y_train_mapped, batch_size=32), epochs=5, validation_data=(x_test, y_test_mapped))

# Verify and save
model.summary()
print("Output shape:", model.output_shape)
model.save('cnn_model.keras')