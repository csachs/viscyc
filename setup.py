import glob
import os
from distutils.cmd import Command
from distutils.command.build_py import build_py

from setuptools import find_packages, setup


class npm_install(Command):
    description = 'load necessary node dependencies via npm install'

    user_options = [('directories=', None, '')]

    @staticmethod
    def prefix_glob_except_py(what, prefix):
        return [
            f[len(prefix) :]
            for f in glob.glob(prefix + what, recursive=True)
            if not f.endswith('.py') and f
        ]

    def initialize_options(self):
        self.directories = ''

    def finalize_options(self):
        if not isinstance(self.directories, list):
            self.directories = self.directories.split(',')

    def run(self):
        for dir_ in self.directories:
            dir_slash = dir_.replace('.', '/')
            old_dir = os.getcwd()
            old_pythonpath = os.environ.get('PYTHONPATH')
            try:
                os.chdir(dir_slash)
                if old_pythonpath:
                    del os.environ['PYTHONPATH']
                self.spawn(['npm', 'install', '.'])
            finally:
                if old_pythonpath:
                    os.environ['PYTHONPATH'] = old_pythonpath
                os.chdir(old_dir)

            if dir_ not in self.distribution.package_data:
                self.distribution.package_data[dir_] = []

            self.distribution.package_data[dir_] += self.prefix_glob_except_py(
                '**', dir_slash + '/'
            )


class build_py_with_npm_install(build_py):
    def run(self):
        self.run_command('npm_install')
        self.finalize_options()  # update package_data
        super().run()


setup(
    name='viscyc',
    version='0.0.1',
    description="Computer Vision based Cycling Cadence/Power Determination and "
    "Bluetooth Transmission - Use your non-smart cross-trainer "
    "with cycling apps!",
    author='Christian Sachs',
    author_email='sachs.christian@gmail.com',
    url='https://github.com/csachs/viscyc',
    packages=find_packages(),
    install_requires=[],
    package_data={'viscyc.manager': ['static/*']},
    license='MIT',
    classifiers=[],
    cmdclass={'build_py': build_py_with_npm_install, 'npm_install': npm_install},
    command_options={'npm_install': {'directories': ('_', ['viscyc.sender'])}},
)
