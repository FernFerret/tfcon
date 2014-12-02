# tfcon

## Installation

    python setup.py install

## Usage

    $ tfcon
    > connect 127.0.0.1
    Password:
    > status
    ...
    > quit

## VirtualEnv
Yep, I do to. Here's how to do it.

    $ cd tfcon
    $ virtualenv venv
    $ source venv/bin/activate
    (venv) $ python setup.py install
    (venv) $ tfcon
