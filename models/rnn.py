import os
import numpy as np
from random import shuffle
import matplotlib.pyplot as plt
from sklearn.model_selection import KFold
from sklearn.preprocessing import LabelBinarizer
from sklearn.preprocessing import MinMaxScaler
from keras.preprocessing.sequence import pad_sequences
from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.layers.recurrent import LSTM
from keras.layers.core import Masking, RepeatVector
from keras.layers.wrappers import TimeDistributed

hurricane_categories = ['TROPICAL STORM', 'TROPICAL DEPRESSION', 'HURRICANE-1', 'HURRICANE-2', 'HURRICANE-3', 'EXTRATROPICAL STORM', 'EXTRATROPICAL DEPRESSION', 'HURRICANE-4', 'EXTRATROPICAL STORM-1', 'EXTRATROPICAL STORM-2', 'HURRICANE-5', 'SUBTROPICAL DEPRESSION', 'SUBTROPICAL STORM', 'XXX', 'DISTURBANCE', 'TROPICAL WAVE', 'LOW', 'TYPHOON-1', 'TYPHOON-2', 'TYPHOON-3', 'TYPHOON-4', 'SUPER TYPHOON-5', 'SUPER TYPHOON-4']

def get_data():
	label_binarizer = LabelBinarizer()
	label_binarizer.fit(hurricane_categories)

	X = []

	for filename in os.listdir('data'):
		if filename[-3:] != 'csv': continue
		file = list(open('data/' + filename, 'r'))
		x = [line.strip().split(',') for line in file[1:]] # ignore header, split up csv
		x = np.array(x)

		x = np.delete(x, 2, axis=1) # time
		x[x == '-'] = 0 # null values

		one_hot = label_binarizer.transform(x[:, -1]) # hurricane to_categorical
		x = np.delete(x, -1, axis=1)
		x = np.hstack((x, one_hot))

		X.append(x.astype(np.float64))

	return X

def preprocess_data(X_in, y_dim=4):
	shuffle(X_in)
	U, X, Y = [], [], []

	# standardize data
	for x in X_in:
		U.extend(x)
	scaler = MinMaxScaler()
	scaler.fit(U)

	for x in X_in:
		if x.shape[0] < 2 * y_dim: #avoid short sequences
			continue

		x = scaler.transform(x)
		X.append(x[:-y_dim])
		Y.append(x[-y_dim:, :2])

	X = pad_sequences(X)
	return np.array(X), np.array(Y), scaler

	split = int(X.shape[0] * test_split)
	return (X[split:], Y[split:]), (X[:split], Y[:split])

def get_model(input_shape, output_shape):
	model = Sequential()
	model.add(Masking(input_shape=input_shape))
	model.add(LSTM(128))
	model.add(RepeatVector(output_shape[0]))
	model.add(LSTM(64, return_sequences=True))
	model.add(TimeDistributed(Dense(output_shape[1])))
	model.compile(loss='mse', optimizer='rmsprop', metrics=['mae'])
	return model

def inverse_scale_y(Y, scaler):
	Y = Y.reshape((-1, 2))
	Y = np.hstack((Y, np.zeros((Y.shape[0], 25))))
	return scaler.inverse_transform(Y)[:,:2]

X = get_data()
X, Y, scaler = preprocess_data(X)

kf = KFold(n_splits=4)
i = 0
y_err = []

for train_index, test_index in kf.split(X):
	i += 1
	X_train, X_test = X[train_index], X[test_index]
	y_train, y_test = Y[train_index], Y[test_index]

	model = get_model(X_train.shape[1:], y_train.shape[1:])
	history = model.fit(X_train, y_train, batch_size=16, epochs=20, validation_data=(X_test, y_test), shuffle=False)

	plt.plot(history.history['loss'], label='train'+str(i))
	plt.plot(history.history['val_loss'], label='test'+str(i))

	y_hat = model.predict(X_test)
	y_pred = inverse_scale_y(y_hat, scaler)
	y_true = inverse_scale_y(y_test, scaler)
	y_err.append(abs((y_pred-y_true)).mean(axis=0))

plt.title('RNN MSE loss')
plt.legend()
plt.show()

y_err = np.array(y_err)
plt.title('RNN avg lat/lon err')
plt.plot(y_err[:,0], label='lat')
plt.plot(y_err[:,1], label='lon')
plt.legend()
plt.show()