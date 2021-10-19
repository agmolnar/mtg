import tensorflow as tf
import sys
from tqdm import tqdm
import numpy as np

class Trainer:
    def __init__(
        self,
        features,
        target,
        model,
        weights = None,
        val_features = None,
        val_target = None,
        val_weights = None,
        clip = 5.0,
    ):
        self.features = features
        self.target = target
        self.model = model
        self.epoch_n = 0
        self.clip = clip
        self.batch_ids = np.arange(len(self.target))
        self.weights = weights
        self.val_features = val_features
        self.val_target = val_target
        self.val_weights = val_weights
    
    def _step(self, batch_features, batch_target, batch_weights):
        with tf.GradientTape() as tape:
            output = self.model(batch_features, training=True)
            loss = self.model.loss(batch_target, output, sample_weight=batch_weights)
            #put regularization here if necessary
        grads = tape.gradient(loss, self.model.trainable_variables)
        if self.clip:
            grads, _ = tf.clip_by_global_norm(grads, self.clip)
        self.model.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
        return loss

    def train(self, n_epochs, batch_size=32, verbose=True, print_keys=[]):
        n_batches = len(self.batch_ids) // batch_size
        end_at = self.epoch_n + n_epochs
        for _ in range(n_epochs):
            self.epoch_n += 1
            np.random.shuffle(self.batch_ids)
            if verbose:
                progress = tqdm(
                    total = n_batches,
                    desc = f'Epoch {self.epoch_n}/{end_at}',
                    unit = 'Batch'
                )
            extras = {k:[] for k in print_keys}
            losses = []
            val_losses = []
            for i in range(n_batches):
                batch_idx = self.batch_ids[i * batch_size:(i+1) * batch_size]
                batch_features = self.features[batch_idx,:]
                batch_target = self.target[batch_idx,:]
                if self.weights is not None:
                    batch_weights = self.weights[batch_idx]
                    batch_weights = batch_weights/batch_weights.sum()
                else:
                    batch_weights = None
                loss = self._step(batch_features, batch_target, batch_weights)
                #run model as if not training on validation data to get out of sample performance
                if self.val_features is not None:
                    val_out = self.model(self.val_features, training=None)
                    val_loss = self.model.loss(self.val_target, val_out, sample_weight=self.val_weights)
                    val_losses.append(np.average(val_loss))
                losses.append(np.average(loss))
                for attr_name in extras.keys():
                    attr = getattr(self.model, attr_name, None)
                    extras[attr_name].append(attr)
                if verbose:
                    if self.val_features is not None:
                        progress.set_postfix(loss=np.average(losses), val_loss=np.average(val_losses), **{k:np.average(v) for k,v in extras.items()})
                    else:
                        progress.set_postfix(loss=np.average(losses), **{k:np.average(v) for k,v in extras.items()})
                    progress.update(1)
            if verbose:
                progress.close()