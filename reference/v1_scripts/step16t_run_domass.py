import os, sys
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import numpy as np
import tensorflow as tf
config = tf.ConfigProto(device_count={'GPU': 0})

print ('\n1\n')
with tf.Graph().as_default() as graph:
    print ('\n2\n')
    with tf.name_scope('input'):
        print ('\n3\n')
        myinputs = tf.placeholder(dtype = tf.float32, shape = (100, 13))
    print ('\n4\n')
    layers = [myinputs]
    layers.append(tf.compat.v1.layers.dense(layers[-1], 64, activation = tf.nn.relu))
    print ('\n5\n')
    preds = tf.compat.v1.layers.dense(layers[-1], 2, activation = tf.nn.softmax)
    print ('\n6\n')
    saver = tf.train.Saver()
    print ('\n7\n')

    with tf.Session(config = config, graph = graph) as sess:
        print ('\n8\n')
        saver.restore(sess, 'domass_epo29')
        print ('\n9\n')
