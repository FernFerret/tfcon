try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Console TF2 Rcon Tool',
    'author': 'FernFerret',
    'url': 'http://www.fernferret.com',
    'download_url': 'http://www.fernferret.com/tf2con',
    'author_email': 'fernferret@gmail.com',
    'version': '0.1',
    'install_requires': ['appdirs', 'colorama', 'termcolor'],
    'packages': ['tfcon'],
    'scripts': ['scripts/tfcon'],
    'name': 'tfcon'
}

setup(**config)
