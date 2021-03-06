import torch
from torch import nn
import torchvision.models


__all__ = ['MiniXception', 'ConvNet', 'PretrConvNet']


class MiniXception(nn.Module):
    def __init__(self, emotion_map, in_channels=1):
        super(MiniXception, self).__init__()
        num_classes = len(emotion_map)
        self.emotion_map = emotion_map

        self.conv1 = nn.Conv2d(in_channels=in_channels, out_channels=8, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(8)
        self.act1 = nn.ReLU()

        self.conv2 = nn.Conv2d(in_channels=8, out_channels=8, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(8)
        self.act2 = nn.ReLU()

        self.blocks = self._make_xception_blocks(in_channels=8, n=4)

        self.sepconv = DepthwiseSeparableConv(in_channels=128, out_channels=16)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(16, num_classes)

    def forward(self, x):
        x = self.act1(self.bn1(self.conv1(x)))
        x = self.act2(self.bn2(self.conv2(x)))
        x = self.blocks(x)
        x = self.sepconv(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x

    @staticmethod
    def _make_xception_blocks(in_channels, n):
        cur_channels = in_channels
        blocks = list()
        for i in range(n):
            blocks.append(MiniXceptionBlock(cur_channels))
            cur_channels *= 2

        return nn.Sequential(*blocks)


class MiniXceptionBlock(nn.Module):
    def __init__(self, in_channels):
        super(MiniXceptionBlock, self).__init__()
        self.in_channels = in_channels
        self.out_channels = 2 * self.in_channels

        self.res_conv = nn.Sequential(
            nn.Conv2d(self.in_channels, self.out_channels, kernel_size=1, stride=2, padding=0),
            nn.BatchNorm2d(self.out_channels)
        )
        self.block = nn.Sequential(
            DepthwiseSeparableConv(self.in_channels, self.out_channels),
            nn.BatchNorm2d(self.out_channels),
            nn.ReLU(),
            DepthwiseSeparableConv(self.out_channels, self.out_channels),
            nn.BatchNorm2d(self.out_channels),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        )

    def forward(self, x):
        return self.res_conv(x) + self.block(x)


class DepthwiseSeparableConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, padding=1):
        super(DepthwiseSeparableConv, self).__init__()
        self.depthwise = nn.Conv2d(in_channels, in_channels, kernel_size=kernel_size, padding=padding, groups=in_channels, bias=False)
        self.pointwise = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False)

    def forward(self, x):
        x = self.depthwise(x)
        x = self.pointwise(x)
        return x


class ResNet18(nn.Module):
    def __init__(self, emotion_map):
        super(ResNet18, self).__init__()
        self.net = torchvision.models.resnet18()
        self.net.fc = nn.Linear(self.net.fc.in_features, len(emotion_map))

    def forward(self, x):
        return self.net(x)


class ConvNet(nn.Module):
    def __init__(self, emotion_map):
        super(ConvNet, self).__init__()

        self.emotion_map = emotion_map

        self.layer1 = self._make_conv_block(in_channels=3, out_channels=16)
        self.layer2 = self._make_conv_block(in_channels=16)
        self.layer3 = self._make_conv_block(in_channels=32)
        self.layer4 = self._make_conv_block(in_channels=64)
        self.layer5 = self._make_conv_block(in_channels=128)
        self.layer6 = self._make_conv_block(in_channels=256)

        self.avgpool = nn.AdaptiveAvgPool2d(output_size=(1, 1))
        self.fc = nn.Linear(in_features=512, out_features=len(emotion_map))

    @staticmethod
    def _make_conv_block(in_channels, out_channels=None):

        if out_channels is None:
            out_channels = in_channels * 2

        layers = list()
        layers.append(nn.Conv2d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=False
            )
        )
        layers.append(nn.BatchNorm2d(num_features=out_channels))
        layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
        layers.append(nn.ReLU())

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.layer6(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x


class PretrConvNet(nn.Module):
    def __init__(self, emotion_map, freeze=True):
        import pretrainedmodels
        super(PretrConvNet, self).__init__()

        self.emotion_map = emotion_map
        self.backbone = pretrainedmodels.resnet34(pretrained='imagenet')

        if freeze:
            for param in self.backbone.parameters():
                param.requires_grad = False

        self.backbone.last_linear = torch.nn.Linear(self.backbone.last_linear.in_features, len(emotion_map))

    def forward(self, x):
        return self.backbone(x)
