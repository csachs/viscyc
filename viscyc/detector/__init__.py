import argparse
import importlib
import importlib.util
import json
import socket
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2


class RawSender:
    def __init__(self, host, port):
        self.host, self.port = host, port

    def send(self, **kwargs):
        message_data = json.dumps(kwargs).encode()

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            s.send(message_data)
            s.close()
        except ConnectionError:
            pass


class HttpSender:
    def __init__(self, url):
        self.url = url

    def send(self, **kwargs):
        json_data = json.dumps(kwargs).encode()
        try:
            urlopen(
                Request(self.url, headers={'Content-type': 'application/json'}),
                data=json_data,
            )
        except (URLError, HTTPError, ConnectionError):
            pass


def create_argparser():
    parser = argparse.ArgumentParser(
        description="watch cross-trainer revolutions via computer vision"
    )

    parser.add_argument('--capture-device', type=int, default=0)
    parser.add_argument('--capture-width', type=int, default=640)
    parser.add_argument('--capture-height', type=int, default=480)

    parser.add_argument('--roi-width', type=int, default=64)
    parser.add_argument('--roi-height', type=int, default=64)

    parser.add_argument('--roi-placement-horizontal', type=int, default=-1)
    parser.add_argument('--roi-placement-vertical', type=int, default=-1)

    parser.add_argument('--threshold', type=int, default=100)

    parser.add_argument('--quiet', default=False, action='store_true')

    parser.add_argument('--no-display', default=False, action='store_true')

    parser.add_argument('--single-jpeg-preview', default=False, action='store_true')

    parser.add_argument('--power-expression', default='1.0*rpm+0')
    parser.add_argument('--load', action='append', default=[])

    parser.add_argument('--target', type=str, default='127.0.0.1:7654')
    parser.add_argument(
        '--http-target', type=str, default='http://127.0.0.1:8901/cadence'
    )

    return parser


def load_file_as_module(file_path):
    name = '_' + Path(file_path).stem

    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def find_power_function(hooks, default):
    calculate_watt = default
    for hook in hooks:
        if getattr(hook, 'calculate_watt', None):
            calculate_watt = getattr(hook, 'calculate_watt')
            print(
                "Using %s.%s as power calculation function."
                % (
                    calculate_watt.__module__,
                    calculate_watt.__name__,
                )
            )
    return calculate_watt


def create_power_expression_function(power_expression):
    frag = f'''
def power_expression(rpm):
    return ({power_expression})
'''
    l, g = {}, {}
    exec(frag, g, l)
    return l['power_expression']


def get_sizes(args):

    size = (args.capture_width, args.capture_height)
    position = [size[0] // 2, size[1] // 2]
    if args.roi_placement_horizontal != -1:
        position[0] = args.roi_placement_horizontal
    if args.roi_placement_vertical != -1:
        position[1] = args.roi_placement_vertical
    roi = args.roi_width, args.roi_height

    return size, position, roi


def prepare_hooks(args):
    hooks = hooks_load(args.load)

    hooks += [RawSender(args.target.split(':')[0], int(args.target.split(':')[1]))]

    if args.http_target:
        hooks += [HttpSender(args.http_target)]

    return hooks


def hooks_load(load):
    hooks = [load_file_as_module(file_name) for file_name in load]
    return hooks


def hooks_call(hooks, what, *args, **kwargs):
    for hook in hooks:
        func = getattr(hook, what, None)
        if func:
            try:
                func(*args, **kwargs)
            except BaseException as e:
                print("Exception occurred while calling %r" % func)
                print(e)


def prepare_preview(display_frame, color, text, position, roi):
    cv2.rectangle(
        display_frame,
        (position[0] - roi[0] // 2, position[1] - roi[1] // 2),
        (position[0] + roi[0] // 2, position[1] + roi[1] // 2),
        color,
    )

    cv2.putText(
        display_frame,
        text,
        org=(0, 24),
        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
        fontScale=1.0,
        color=(0, 255, 0),
    )

    return display_frame


COLOR_INSIDE = (0, 0, 255)
COLOR_OUTSIDE = (0, 255, 0)


def main_loop(
    capture_function,
    position,
    roi,
    threshold,
    hook_send,
    quiet,
    preview,
    return_jpg=False,
):
    last_timepoint = None
    last_acquisition = None
    inside = False
    last_rpm = None

    rev_count = 0

    while True:

        frame_input = capture_function()

        timepoint = time.time()

        frame_grayscale = cv2.cvtColor(frame_input, cv2.COLOR_BGR2GRAY)

        _, frame_binary = cv2.threshold(
            frame_grayscale, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        frame_roi = frame_binary[
            position[1] - roi[1] // 2 : position[1] + roi[1] // 2,
            position[0] - roi[0] // 2 : position[0] + roi[0] // 2,
        ]

        mean_value = frame_roi.mean()

        color = COLOR_OUTSIDE

        text = "RPM: % 2.2f Revs: %04d" % (
            last_rpm if last_rpm else 0.0,
            rev_count,
        )

        if last_acquisition:
            text += " FPS: %2.1f" % (1.0 / (timepoint - last_acquisition))

        last_acquisition = timepoint

        if mean_value < threshold:
            color = COLOR_INSIDE

            if not inside and last_timepoint:
                delta = timepoint - last_timepoint

                rpm = (1.0 / delta) * 60.0

                rev_count += 1

                last_rpm = rpm

                hook_send(rev_count=rev_count, rpm=rpm)

                if not quiet:
                    print(text)

            inside = True
            last_timepoint = timepoint

        else:

            inside = False

        if preview:
            display_frame = prepare_preview(
                frame_input.copy(), color, text, position, roi
            )

            if return_jpg:
                _, result = cv2.imencode('.jpg', display_frame)
                return result.tostring()
            else:
                cv2.imshow("Viscyc Detector", display_frame)
                if cv2.waitKey(1) & 0xff == ord('q'):
                    break


def main(args=None, return_instead_print=False):
    if args is None:
        args = sys.argv[1:]

    parser = create_argparser()
    args = parser.parse_args(args)

    power_expression = args.power_expression

    calculate_watt = create_power_expression_function(power_expression)

    hooks = prepare_hooks(args)

    calculate_watt = find_power_function(hooks, default=calculate_watt)

    size, position, roi = get_sizes(args)

    capture = cv2.VideoCapture(args.capture_device)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])

    def capture_function():
        return capture.read()[1]

    def hook_send(rev_count=0, rpm=0):
        return hooks_call(
            hooks, 'send', watts=calculate_watt(rpm), rev_count=rev_count, rpm=rpm
        )

    try:
        hooks_call(hooks, 'start')
        hook_send()
        print("Beginning processing")
        result = main_loop(
            capture_function,
            position,
            roi,
            args.threshold,
            hook_send,
            args.quiet,
            preview=not args.no_display or args.single_jpeg_preview,
            return_jpg=args.single_jpeg_preview,
        )
        if result:
            if return_instead_print:
                return result
            else:
                sys.stdout.buffer.write(result)

    finally:
        capture.release()
        cv2.destroyAllWindows()
        hook_send()
        hooks_call(hooks, 'stop')
        print("Halted processing")
