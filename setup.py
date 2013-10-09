from setuptools import setup, Command, find_packages


class PyTest(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys
        import subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


setup(
    name='waffle',
    url='http://github.com/alecthomas/waffle',
    download_url='http://pypi.python.org/pypi/waffle',
    version='0.3.0',
    options=dict(egg_info=dict(tag_build='')),
    description='Waffle - A Dependency-Injection-based application framework for Python',
    long_description='See http://github.com/alecthomas/waffle for details.',
    license='BSD',
    platforms=['any'],
    packages=find_packages(),
    author='Alec Thomas',
    author_email='alec@swapoff.org',
    install_requires=[
        'setuptools >= 0.6b1',
        'injector',
        'argh',
    ],
    cmdclass={'test': PyTest},
    )
