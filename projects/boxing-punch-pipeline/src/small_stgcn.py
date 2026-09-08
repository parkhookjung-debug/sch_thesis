"""Compact ST-GCN for small-dataset boxing punch classification.

Why so small:
  Original STGCN: 1.77M params, training set N~=1300, single subject.
  That ratio (~700 samples per param) leads to severe memorization.
  This variant drops to ~50K params, adds dropout, and uses fewer blocks.

Architecture:
  data_bn -> [block 32] -> [block 32] -> [block 64 stride=2] -> GAP -> FC

Each block: GraphConv(1x1) + TempConv(k=7) with residual + BN + Dropout.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from pose_schema import NUM_JOINTS, SELF_LINKS, SKELETON_EDGES


def normalized_adjacency(num_nodes: int = NUM_JOINTS) -> torch.Tensor:
    a = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    for i, j in SELF_LINKS + SKELETON_EDGES:
        a[i, j] = 1.0
        a[j, i] = 1.0
    d = a.sum(axis=1)
    d[d == 0.0] = 1.0
    d_inv = np.diag(np.power(d, -0.5))
    return torch.tensor(d_inv @ a @ d_inv, dtype=torch.float32)


class GraphConv(nn.Module):
    def __init__(self, in_c: int, out_c: int):
        super().__init__()
        self.proj = nn.Conv2d(in_c, out_c, kernel_size=1)

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        return self.proj(torch.einsum("nctv,vw->nctw", x, adj))


class CompactBlock(nn.Module):
    def __init__(self, in_c: int, out_c: int, stride: int = 1, dropout: float = 0.4, kt: int = 7):
        super().__init__()
        self.gcn = GraphConv(in_c, out_c)
        pad = (kt - 1) // 2
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_c, out_c, kernel_size=(kt, 1), stride=(stride, 1), padding=(pad, 0)),
            nn.BatchNorm2d(out_c),
            nn.Dropout(dropout),
        )
        if in_c == out_c and stride == 1:
            self.residual = nn.Identity()
        else:
            self.residual = nn.Sequential(
                nn.Conv2d(in_c, out_c, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_c),
            )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        return self.relu(self.tcn(self.gcn(x, adj)) + self.residual(x))


class SmallSTGCN(nn.Module):
    def __init__(self, in_channels: int, num_classes: int,
                 num_joints: int = NUM_JOINTS, dropout: float = 0.4,
                 base_channels: int = 32):
        super().__init__()
        self.register_buffer("adjacency", normalized_adjacency(num_joints))
        self.data_bn = nn.BatchNorm1d(in_channels * num_joints)

        c1 = base_channels
        c2 = base_channels * 2
        self.layers = nn.ModuleList([
            CompactBlock(in_channels, c1, stride=1, dropout=dropout),
            CompactBlock(c1, c1, stride=1, dropout=dropout),
            CompactBlock(c1, c2, stride=2, dropout=dropout),
        ])
        self.head_dropout = nn.Dropout(dropout)
        self.head = nn.Linear(c2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n, c, t, v = x.shape
        x = x.permute(0, 3, 1, 2).contiguous().view(n, v * c, t)
        x = self.data_bn(x)
        x = x.view(n, v, c, t).permute(0, 2, 3, 1).contiguous()
        for layer in self.layers:
            x = layer(x, self.adjacency)
        x = x.mean(dim=(2, 3))
        x = self.head_dropout(x)
        return self.head(x)
