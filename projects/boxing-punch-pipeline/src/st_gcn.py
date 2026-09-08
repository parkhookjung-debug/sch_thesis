from __future__ import annotations

import numpy as np
import torch
from torch import nn

from pose_schema import NUM_JOINTS, SELF_LINKS, SKELETON_EDGES


def normalized_adjacency(num_nodes: int = NUM_JOINTS) -> torch.Tensor:
    adjacency = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    for i, j in SELF_LINKS + SKELETON_EDGES:
        adjacency[i, j] = 1.0
        adjacency[j, i] = 1.0

    degree = adjacency.sum(axis=1)
    degree[degree == 0.0] = 1.0
    degree_inv_sqrt = np.diag(np.power(degree, -0.5))
    normalized = degree_inv_sqrt @ adjacency @ degree_inv_sqrt
    return torch.tensor(normalized, dtype=torch.float32)


class GraphConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.proj = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        x = torch.einsum("nctv,vw->nctw", x, adjacency)
        return self.proj(x)


class STGCNBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1, dropout: float = 0.2):
        super().__init__()
        self.gcn = GraphConv(in_channels, out_channels)
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=(9, 1),
                stride=(stride, 1),
                padding=(4, 0),
            ),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout),
        )

        if in_channels == out_channels and stride == 1:
            self.residual = nn.Identity()
        else:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        return self.relu(self.tcn(self.gcn(x, adjacency)) + self.residual(x))


class STGCN(nn.Module):
    def __init__(self, in_channels: int, num_classes: int, num_joints: int = NUM_JOINTS):
        super().__init__()
        self.register_buffer("adjacency", normalized_adjacency(num_joints))
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)

        self.layers = nn.ModuleList(
            [
                STGCNBlock(in_channels, 64),
                STGCNBlock(64, 64),
                STGCNBlock(64, 64),
                STGCNBlock(64, 128, stride=2),
                STGCNBlock(128, 128),
                STGCNBlock(128, 256, stride=2),
                STGCNBlock(256, 256),
            ]
        )
        self.head = nn.Linear(256, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n, c, t, v = x.shape
        x = x.permute(0, 3, 1, 2).contiguous().view(n, v * c, t)
        x = self.data_bn(x)
        x = x.view(n, v, c, t).permute(0, 2, 3, 1).contiguous()

        for layer in self.layers:
            x = layer(x, self.adjacency)

        x = x.mean(dim=(2, 3))
        return self.head(x)
