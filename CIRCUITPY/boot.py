# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT


import storage


# If the switch pin is connected to ground CircuitPython can write to the drive
storage.remount("/", False)

