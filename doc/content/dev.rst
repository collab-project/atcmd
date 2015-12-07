Development
===========

Tests
-----

Make sure to install the development dependencies first::

  pip install -r requirements-dev.txt

To run the tests with the default Python in your environment::

  python -m unittest discover -v

Run tests with Tox_ on both Python 2.7 and 3.4::

  tox

To create a coverage report::

  coverage run --source=. --rcfile=.coveragerc -m unittest discover -v
  coverage html

Open ``htmlcov/index.html`` in your browser to view the test report.


.. _tox: https://testrun.org/tox/latest/
