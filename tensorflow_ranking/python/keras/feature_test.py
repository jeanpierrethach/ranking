# Copyright 2020 The TensorFlow Ranking Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Test for Keras feature transformations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import six

import tensorflow.compat.v2 as tf

from tensorflow_ranking.python.keras import feature


def _context_feature_columns():
  return {
      'query_length':
          tf.feature_column.numeric_column(
              'query_length', shape=(1,), default_value=0, dtype=tf.int64)
  }


def _example_feature_columns():
  return {
      'utility':
          tf.feature_column.numeric_column(
              'utility', shape=(1,), default_value=0.0, dtype=tf.float32),
      'unigrams':
          tf.feature_column.embedding_column(
              tf.feature_column.categorical_column_with_vocabulary_list(
                  'unigrams',
                  vocabulary_list=[
                      'ranking', 'regression', 'classification', 'ordinal'
                  ]),
              dimension=10)
  }


def _features():
  return {
      'query_length':
          tf.convert_to_tensor(value=[[1], [2]]),
      'utility':
          tf.convert_to_tensor(value=[[[1.0], [0.0]], [[0.0], [1.0]]]),
      'unigrams':
          tf.SparseTensor(
              indices=[[0, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0]],
              values=['ranking', 'regression', 'classification', 'ordinal'],
              dense_shape=[2, 2, 1]),
      'example_feature_size':
          tf.convert_to_tensor(value=[1, 2])
  }


clone_keras_obj = lambda obj: obj.__class__.from_config(obj.get_config())


class KerasInputsTest(tf.test.TestCase):

  def setUp(self):
    super(KerasInputsTest, self).setUp()
    self.context_feature_columns = _context_feature_columns()
    self.example_feature_columns = _example_feature_columns()

  def test_keras_inputs_dynamic_list_shape(self):
    keras_inputs = feature.create_keras_inputs(
        context_feature_columns=self.context_feature_columns,
        example_feature_columns=self.example_feature_columns,
        size_feature_name=None)

    self.assertEqual(keras_inputs['query_length'].shape.as_list(), [None, 1])
    self.assertEqual(keras_inputs['query_length'].dtype, tf.int64)

    self.assertEqual(keras_inputs['utility'].shape.as_list(), [None, None, 1])
    self.assertEqual(keras_inputs['utility'].dtype, tf.float32)

    self.assertEqual(keras_inputs['unigrams'].dtype, tf.string)


class EncodeListwiseFeaturesTest(tf.test.TestCase):

  def setUp(self):
    super(EncodeListwiseFeaturesTest, self).setUp()
    self.context_feature_columns = _context_feature_columns()
    self.example_feature_columns = _example_feature_columns()

    # Batch size = 2, list_size = 2.
    self.features = _features()
    self.listwise_dense_layer = feature.EncodeListwiseFeatures(
        context_feature_columns=self.context_feature_columns,
        example_feature_columns=self.example_feature_columns)

  def test_get_config(self):
    # Check save and restore config.
    restored_layer = clone_keras_obj(self.listwise_dense_layer)
    self.assertEqual(restored_layer.context_feature_columns,
                     self.context_feature_columns)
    self.assertEqual(restored_layer.example_feature_columns,
                     self.example_feature_columns)

  def test_listwise_dense_layer(self):
    context_features, example_features = self.listwise_dense_layer(
        inputs=self.features, training=False)
    self.assertAllInSet(['query_length'], set(six.iterkeys(context_features)))
    self.assertAllInSet(['unigrams', 'utility'],
                        set(six.iterkeys(example_features)))
    self.assertAllEqual(example_features['unigrams'].get_shape().as_list(),
                        [2, 2, 10])
    self.assertAllEqual(context_features['query_length'], [[1], [2]])
    self.assertAllEqual(example_features['utility'],
                        [[[1.0], [0.0]], [[0.0], [1.0]]])

  def test_create_keras_inputs(self):
    keras_inputs = feature.create_keras_inputs(
        context_feature_columns=self.context_feature_columns,
        example_feature_columns=self.example_feature_columns,
        size_feature_name='example_list_size')

    self.assertCountEqual(
        keras_inputs.keys(),
        list(self.context_feature_columns.keys()) +
        list(self.example_feature_columns.keys()) + ['example_list_size'])


class GenerateMaskTest(tf.test.TestCase):

  def setUp(self):
    super(GenerateMaskTest, self).setUp()
    self.context_feature_columns = _context_feature_columns()
    self.example_feature_columns = _example_feature_columns()
    # Batch size = 2, list_size = 2.
    self.features = _features()
    self.mask_generator_layer = feature.GenerateMask(
        example_feature_columns=self.example_feature_columns,
        size_feature_name='example_feature_size')

  def test_get_config(self):
    # Check save and restore config.
    restored_layer = clone_keras_obj(self.mask_generator_layer)
    self.assertEqual(restored_layer.example_feature_columns,
                     self.example_feature_columns)

  def test_mask_generator_layer(self):
    mask = self.mask_generator_layer(inputs=self.features, training=False)
    expected_mask = [[True, False], [True, True]]
    self.assertAllEqual(expected_mask, mask)


if __name__ == '__main__':
  tf.enable_v2_behavior()
  tf.test.main()
