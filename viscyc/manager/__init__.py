import argparse
import json
import sys
from io import BytesIO
from pathlib import Path
from subprocess import PIPE, Popen

from flask import Flask, jsonify, render_template, request, send_file

from ..detector import main as detector_main

app = Flask(
    __name__,
    static_url_path='/node_modules',
    static_folder='../sender/node_modules',
    template_folder='static',
)


class Service:
    COMMAND = []
    ARGS = []

    def __init__(self):
        self.process = None
        self.arguments = self.ARGS.copy()

    def start(self, capture=False):
        if self.process is None:
            call = self.COMMAND + self.arguments
            print(f"Starting {call!r}")
            self.process = Popen(call, stdout=PIPE if capture else None)

    def stop(self):
        if self.process:
            print(f"Stopping {self.COMMAND!r}")
            self.process.kill()
        self.process = None

    @property
    def running(self):
        return self.process and self.process.poll() is None


class DetectorService(Service):
    COMMAND = [sys.executable, '-m', 'viscyc.detector']
    ARGS = ['--no-display']

    def preview_process(self):
        running = self.running
        self.stop()

        self.arguments.append('--single-jpeg-preview')

        self.start(capture=True)
        result = self.process.stdout.read()
        self.stop()

        self.arguments.remove('--single-jpeg-preview')

        if running:
            self.start()

        return result

    def preview(self):
        return detector_main(
            self.ARGS + ['--single-jpeg-preview'], return_instead_print=True
        )


class SenderService(Service):
    COMMAND = [sys.executable, '-m', 'viscyc.sender']
    ARGS = []


class Manager:
    services = dict(
        detector=DetectorService(),
        sender=SenderService(),
    )

    cadence = dict()


@app.route('/')
def index():
    return render_template('interface.html')


@app.route('/status/<service>', methods=['GET', 'POST'])
def status(service):

    assert service in ('detector', 'sender')

    instance = Manager.services[service]

    if request.method == 'POST':
        if request.json['active']:
            instance.start()
        else:
            instance.stop()

    return jsonify(dict(active=instance.running))


@app.route('/cadence', methods=['GET', 'POST'])
def cadence():
    if request.method == 'POST':
        Manager.cadence = request.json

    return jsonify(Manager.cadence)


@app.route('/camera.jpg')
def camera():
    return send_file(
        BytesIO(Manager.services['detector'].preview()),
        mimetype='image/jpg',
        cache_timeout=-1,
    )


def configure_args(args, service_name, configuration_key):
    additional_args = getattr(args, configuration_key, None)
    if additional_args:
        Manager.services[service_name].arguments += additional_args
        print(
            f"{service_name} args are now: {Manager.services[service_name].arguments!r}"
        )


def create_argparser():
    parser = argparse.ArgumentParser(description="Viscyc Manager")

    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8901)

    parser.add_argument(
        '--config', type=str, default=str(Path('~/.viscyc/config.json').expanduser())
    )
    parser.add_argument(
        '--load-dir', type=str, default=str(Path('~/.viscyc/load.d').expanduser())
    )

    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = create_argparser()

    unparsed_args = args

    args = parser.parse_args(unparsed_args)

    config_file = Path(args.config)

    if config_file.exists():
        for k, v in json.loads(config_file.read_text()).items():
            setattr(args, k, v)

    args = parser.parse_args(unparsed_args, args)

    load_dir = Path(args.load_dir)
    if load_dir.is_dir():
        for load_file in load_dir.glob('*.py'):
            Manager.services['detector'].arguments += ['--load', str(load_file)]

    configure_args(args, 'sender', 'sender_args')
    configure_args(args, 'detector', 'detector_args')

    app.run(args.host, args.port)
