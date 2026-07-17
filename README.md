# Native Headset Battery

Display the battery level of a Logitech wireless headset directly in KDE Plasma's Power & Battery panel.

The goal of this project is to make headset battery information feel native, update automatically, and appear alongside other battery-powered devices such as mice and keyboards.

## Background

While experimenting with Linux as my main operating system, I quickly noticed a small but annoying limitation: my Logitech mouse appeared correctly in KDE Plasma's Power & Battery panel, but my Logitech headset did not.

I wanted a simple and native-looking way to check the headset battery level without opening a separate application or running a command manually.

[HeadsetControl](https://github.com/Sapd/HeadsetControl) already provided reliable access to the headset's battery information, so I decided to extend that functionality and expose it through Linux's native `power_supply` subsystem.

The result is a headset battery device that is detected by UPower and displayed directly in KDE Plasma.
