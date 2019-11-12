from torch import nn


class TinyYolo(nn.Module):
    """Tiny YOLOv1 model. 12.3 millions trainable parametrs."""
    def __init__(self):
        super(TinyYolo, self).__init__()
        self.S = 6   # grid size
        self.B = 2   # number of bbox
        self.C = 1   # number of classes

        self.layer1 = self._make_conv_block(in_channels=3, out_channels=16)
        self.layer2 = self._make_conv_block(in_channels=16)
        self.layer3 = self._make_conv_block(in_channels=32)
        self.layer4 = self._make_conv_block(in_channels=64)
        self.layer5 = self._make_conv_block(in_channels=128)
        self.layer6 = self._make_conv_block(in_channels=256)

        self.conv1 = nn.Conv2d(in_channels=512, out_channels=1024, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(in_channels=1024, out_channels=256, kernel_size=3, stride=1, padding=1)
        self.fc = nn.Linear(in_features=256*self.S*self.S, out_features=self.S*self.S*(5*self.B + self.C))
        self.sigmoid = nn.Sigmoid()

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
                padding=1
            )
        )
        layers.append(nn.BatchNorm2d(num_features=out_channels))
        layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
        layers.append(nn.LeakyReLU(negative_slope=0.1, inplace=True))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.layer6(x)
        x = self.conv1(x)
        x = self.conv2(x)
        x = x.view((x.size(0), -1))
        x = self.fc(x)
        x = self.sigmoid(x)

        x = x.view(-1, self.S, self.S, 5 * self.B + self.C)
        return x
