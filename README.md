# Viscyc

Computer Vision based Cycling Cadence/Power Determination and Bluetooth Transmission – Use your non-smart cross-trainer with cycling apps!
<p align="center">
    <img src="https://csachs.github.io/viscyc/screenshot.png" alt="Viscyc comes with a webinterface for remote control" height="400"/> <img src="https://csachs.github.io/viscyc/view_zwift.gif" alt="Viscyc can be used with cycling apps, such as Zwift" height="400"/><br />
<img src="https://csachs.github.io/viscyc/view_external.gif" alt="Make your non-smart cross-trainer compatible with cycling apps using a Raspberry Pi Zero" height="200"/> <img src="https://csachs.github.io/viscyc/view_camera.gif" alt="Detection via Computer Vision - The image is Otsu thresholded and the mean intensity of the ROI (region of interest) checked"  height="200"/> <br />
</p>

## Overview

Viscyc consists of three loosely coupled components: the computer vision-based revolution detection (using [OpenCV](https://github.com/opencv/opencv)), the cadence/power sending via Bluetooth (using the excellent [Zwack](https://github.com/paixaop/zwack) library), and a webinterface to control the components.

## Installation

For a Raspberry Pi with raspbian (buster), first install the following packages:

```bash
sudo apt update
sudo apt install nodejs npm python3 python3-pip python3-opencv python3-flask
```

Install Viscyc via `pip`.

*Note*: If you use a different platform, please install the necessary dependencies beforehand. Viscyc does **not** specify the necessary dependencies via `setup.py`, because OpenCV is notoriously hard to install reliable that way, and it can often lead to distribution package clashes.
```bash
pip3 install --user https://github.com/csachs/viscyc/archive/refs/heads/main.zip
```

You can automatically create, enable and start a `systemd` service file for the current user (e.g. `pi` on raspbian), and furthermore, to fully utilize it, `node` must be given full access to the Bluetooth stack, and the  `pi` user must be allowed to keep processes running even when not being logged in, all will be done by calling:
```bash
python3 -m viscyc.install
```

**WARNING**: Viscyc's Manager component opens a port for its HTTP webinterface. There is no authentication, and a person with access to the webinterface can view the camera. Please ensure that no unauthorized access is possible!

## Configuration

The individual components have certain command-line options, a list of which can be gained by calling the *individual* component with `--help`:

```bash
python3 -m viscyc.detector --help
python3 -m viscyc.sender --help
python3 -m viscyc.manager --help
```

To configure all components as run via `viscyc.manager`, create a file `~/.viscyc/config.json`:
```json
{
    "host": "0.0.0.0",
    "port": 8901,
    "sender_args": ["--additional-args", "--go-here"],
    "detector_args": ["--similarly", "here"]
}
```

Furthermore, you can add Python scripts (`.py`) in the folder `~/.viscyc/load.d` which will automatically be loaded (when started via `viscyc.manager`), such as for the power calculation, or to hook revolution events and e.g. control other things.

*Hint:* In the `examples/` directory, a power function for the Christopeit AM-6 cross trainer is present, as well as little script to control a Smart Fan power dependent (think airflow while driving).

```python
# hook script example
def calculate_watt(rpm):
    return 1.0 * rpm  # you need to determine this ... see Power calculation below

def start():
    pass  # called when a training is started

def stop():
    pass  # called when a training is stopped

def send(rpm, rev_count, watts):
    pass  # called when a revolutions has been detected (blocking, keep it fast)
    
```

## Usage

When Viscyc is started, you can control the webinterface at `http://<host>:8901`.

The computer vision-based detection / Bluetooth sending services don't start by automatically, to keep processing load low on embedded platforms like the Raspberry Pi (Zero); you can start them via the webinterface.
You can get a camera view (stationary, refreshable) to first properly position your camera to detect your trainer. Put a dark feature, such as the levers, in the rectangular region of interest.

When all is set up, the services can be started. The webinterface will show cadence and power (after movement occurs), and you're ready to use it with a training app such as Zwift.

After usage, the services can be stopped again.

## Power Calculation

In order to calculate the current wattage from the rotations per minute value, a function modeling the correlation must be provided by the user, specifically matching their training device.

I've fitted a function for the Christopeit AM-6 cross-trainer, and an example how the values were obtained is in `examples/Christopeit AM-6.ipynb`.

Please make sure the power calculations by the function you provide are correct to properly match the virtual training experience to your real world training. Don't cheat. If your trainer e.g. shows power on the display, try some different RPM levels and check if the transmitted wattage matches the one your trainer tells you.

## Hardware Requirements

Viscyc has been tweaked to run on a Raspberry Pi Zero, which, if fitted with the Raspberry Pi camera, unites all necessary hardware in a nice package, it has however been tested with Linux and macOS as well, using webcams as camera sources. Theoretically, all necessary libraries should run on Windows as well, but I have not tested it.

## Computer Vision

Nothing fancy. The camera image is thresholded using Otsu's method, and the mean intensity value of a centered, rectangular region of interest (ROI) is assessed.
If something dark enters this region, a rotation will be detected. This simple approach was found to work fast and robust, even on embedded platforms like the Raspberry Pi.

## Background

Given the current situation greatly reduced opportunities for exercise, I was looking into ways to make working out at home less boring.
Online platforms like Zwift promised more fun and motivation, but require specific hardware. Since I already had plain old non-smart cross-trainer, I was wondering if I could somehow make it smart to use it for such gamification approaches: Theoretically, hooking up a logic analyzer to the control panel wiring should give some insights if a smart controller could be easily developed… but I didn't have my logic analyzer at hand, and less intrusive approaches would probably be easier to  implement. After seeing that Bluetooth cadence sensors are cheaply available, I bought some and played around with them: Sadly, I noticed that mine only sent cadence, not speed, and even after a lot of CSC Bluetooth 4.0 LE specification reading and begging the sensors to send speed into cadence, I could not get the results I needed. More development work on an initial prototype of receiving cadence on a PC and resending speed signals showed however a much graver problem: The sensors, being designed for relatively high RPM bicycle pedal cranks, would not reliably transmit a rotation event for the slower cross-trainer wheel…

At this point I scrapped the idea of using sensors and moved to a domain I am more at home in: computer vision. As expected, *watching* a large object repeatedly enter and leave a camera frame was ridiculously simple and reliable to detect, and given a wide set of pre-existing libraries, with relatively few lines of code, a working prototype could be established. Some testing, tweaking and polishing later, Viscyc was born.

## License

MIT