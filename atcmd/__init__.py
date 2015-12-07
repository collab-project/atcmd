# Copyright (c) Collab and contributors.
# See LICENSE for details.

#: Application version.
__version__ = (0, 1, 0)


def short_version(version=None):
    """
    Return the short version number.

    For example: ``1.0.0``

    :param version: A tuple like ``(major, minor, micro, releaselevel)``.
        Default is :py:attr:`__version__`.
    :type version: tuple
    :rtype: str
    """
    v = version or __version__
    return '.'.join([str(x) for x in v[:3]])


def get_version(version=None):
    """
    Return the full version number, including rc, beta etc. tags.

    For example: ``2.0.0a1``

    :param version: A tuple like ``(major, minor, micro, releaselevel)``.
        Default is :py:attr:`__version__`.
    :type version: tuple
    :rtype: str
    """
    v = version or __version__
    if len(v) == 4:
        return '{0}{1}'.format(short_version(v), v[3])

    return short_version(v)


#: Library version number string.
version = get_version()

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler
logging.getLogger(__name__).addHandler(NullHandler())
