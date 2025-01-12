#!/usr/bin/env python

# Copyright 2017
# ==============================================================================

"""Converts HDF5 data files to TFRecords file format with Example protos."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import sys

import tensorflow as tf
import numpy as np
import h5py


FLAGS = None


def read_hdf5(path):

    sets_to_read = ['image_1', 'image_2', 'image_3']
    attrs_to_read = ['space_group']
    f = h5py.File(path, "r")
    samples = keys = list(f.keys())
    samples = [f[key] for key in keys]
    images = [] # A list of dictionary (key : val) = ('sample_image_whatever' : image in np.array)
    labels = [] # A list of dictionary (key : val) = ('sample_space_group' : space group in np.array)
    
    # For each sample, extract 3 images and space group as dicts of np.array
    for sample in samples:
        images.append({str(sample) + s: np.array(cbed) for s, cbed in zip(sets_to_read, samples['cbed_stack'])})
        labels.append({str(sample) + a: np.array(sample.attrs[a]) for a in attrs_to_read})
    f.close()
    
    return (images, labels)


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def _float_array_feature(array):
    return tf.train.Feature(float_list=tf.train.FloatList(value=array))


def _int_array_feature(array):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=array))


def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def convert_to(directory, dataset_name):

    files = sorted([os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.h5')])

    filename = os.path.join(directory, dataset_name + '.tfrecords')
    print('Writing', filename)

    with tf.python_io.TFRecordWriter(filename) as writer:

        unique_values = {}

        for file in files:
            try:
                data = read_hdf5(file)
            except OSError:
                print("Could not read {}. Skipping.".format(file))
                continue

            point_cloud = data['point_cloud']
            labels = data['obj_labels']

            u, counts = np.unique(labels, return_counts=True)
            for u, count in zip(u, counts):
                if u in unique_values:
                    unique_values[u] += count
                else:
                    unique_values[u] = count

            num_points = point_cloud.shape[0]

            if num_points != labels.shape[0]:
                raise RuntimeError("Point cloud size does not match label size in {} ({} vs. {})"
                                   .format(file, point_cloud.shape[0], labels.shape[0]))

            example = tf.train.Example(
                features=tf.train.Features(
                    feature={
                        'num_points': _int64_feature(num_points),
                        'points': _float_array_feature(point_cloud.flatten()),
                        'label': _int_array_feature(labels),
                    }
                )
            )
            writer.write(example.SerializeToString())

        print("Unique values in dataset '{}': {}".format(dataset_name, unique_values))


def main(unused_argv):
    convert_to(FLAGS.train_dir, 'train_tfrecord')


if __name__ == '__main__':

    def is_valid_folder(x):
        """
        'Type' for argparse - checks that file exists but does not open.
        """
        x = os.path.expanduser(x)
        if not os.path.isdir(x):
            raise argparse.ArgumentTypeError("{0} is not a directory".format(x))
        return x

    parser = argparse.ArgumentParser()
    parser.add_argument('--train_dir', metavar='directory', type=is_valid_folder)
    parser.add_argument('--val_dir', metavar='directory', type=is_valid_folder)

    FLAGS, unparsed = parser.parse_known_args()
    tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
