import os
import re
import setuptools


def find_version(filename):
    with open(filename) as f:
        text = f.read()
    match = re.search(r"^asqlite3_version_str = '(.*)'$", text, re.MULTILINE)
    if not match:
        raise RuntimeError('cannot find version')
    return match.group(1)


tld = os.path.abspath(os.path.dirname(__file__))
version = find_version(os.path.join(tld, 'asqlite3', '__init__.py'))


setuptools.setup(
    name='py-asqlite3',
    version=version,
    scripts=[],
    python_requires='>=3.8',
    install_requires=[],
    packages=['asqlite3'],
    description='Async wrapper for sqlite3',
    author='Neil Booth',
    author_email='kyuupichan@pm.me',
    license='MIT Licence',
    url='https://github.com/kyuupichan/asqlite3',
    long_description='Async wrapper for sqlite3',
    download_url=('https://github.com/kyuupichan/asqlite3/archive/'
                  f'{version}.tar.gz'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        "Programming Language :: Python :: 3.8",
        "Topic :: Database",
    ],
)
