import numpy as np
import torch
import torch.nn as nn

from encoder import Encoder
from decoder import Decoder
from patch import Patch
from prototype import Prototypes


class SemanticAutoencoder(nn.Module):
    def __init__(self, input_size, encoded_patch_size, num_prototypes):
        super(SemanticAutoencoder, self).__init__()
        self._is_cuda = False

        self.num_prototypes = num_prototypes

        self._encoder_net = Encoder(input_size)
        self._decoder_net = Decoder(self._encoder_net.num_out_channels)

        encoded_output_size = self._encoder_net.output_size
        assert encoded_patch_size < encoded_output_size
        self._patches = Patch.from_spec(
            (encoded_output_size, encoded_output_size),
            (encoded_patch_size, encoded_patch_size))

        dim_prototypes = self._encoder_net.num_out_channels * (encoded_patch_size ** 2)
        self.prototypes = Prototypes(num_prototypes + 1, dim_prototypes, padding_idx=0)
        self.prototypes.weight.requires_grad = False  # freeze embeddings

    def cuda(self, device_id=None):
        super(SemanticAutoencoder, self).cuda(device_id)
        self._is_cuda = True

    def forward(self, x):
        z = self._encoder_net(x)
        reconstructed_x = self._decoder_net(z)

        z_patches = [patch(z) for patch in self._patches]  # [patch1:Tensor(batch_size, dim), patch2, ...]
        z_patches = torch.stack(z_patches)  # num_patches, batch_size, embedding_dim
        z_patches = z_patches.transpose(0, 1)  # batch_size, num_patches, embedding_dim

        return z, z_patches, reconstructed_x

    def get_nearest_dataset_patches_for_prototypes(self, dataset):
        put_on_gpu = lambda x_: x_.cuda() if self._is_cuda else x_

        all_patches = list()
        all_patches_indices = list()
        for i, (image, _, _, _) in enumerate(dataset):
            x = image.view((1,) + image.size())
            x = put_on_gpu(torch.autograd.Variable(x))
            z, z_patches, reconstructed_x = self.forward(x)

            patches = z_patches[0]
            for j, patch in enumerate(patches):
                all_patches.append(patch.data.cpu().numpy())
                all_patches_indices.append((i, j))
        all_patches = np.array(all_patches)

        prototype_patches = dict()
        for k in range(1, self.num_prototypes + 1):
            prototype = self.prototypes.weight[k].data.cpu().numpy()

            dists = np.linalg.norm(prototype - all_patches, ord=2, axis=1)

            nearest_patch_idx = np.argmin(dists)
            nearest_patch = all_patches[nearest_patch_idx]
            nearest_image_patch_idx = all_patches_indices[nearest_patch_idx]  # (image_idx, patch_idx)
            prototype_patches[k] = (nearest_image_patch_idx, nearest_patch)

        return prototype_patches

    def reproject_prototypes_to_dataset(self, dataset):
        prototype_patches = self.get_nearest_dataset_patches_for_prototypes(dataset)

        for k, (nearest_image_patch_idx, nearest_patch) in prototype_patches.items():
            self.prototypes.weight[k].data = torch.FloatTensor(nearest_patch)

        return prototype_patches

    def get_receptive_field(self, patch_idx):
        return (0, 0), (50, 50)


if __name__ == '__main__':
    from itertools import ifilter
    input_image_size = 64
    expected_image_shape = (3, input_image_size, input_image_size)
    input_tensor = torch.autograd.Variable(torch.rand(5, *expected_image_shape))

    net = SemanticAutoencoder(input_image_size, 1, 10)
    print net
    for p in ifilter(lambda p: p.requires_grad, net.parameters()):
        print p.size()
    # print
    # z, z_patches, reconstructed_x = net(input_tensor)
    # print z.size()
    # print reconstructed_x.size()
    # print z_patches[0].size()
    # print len(z_patches)

    print net.prototypes.weight[1]