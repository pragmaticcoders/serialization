from __future__ import absolute_import

import pytest

from .common_serialization import ConverterTestHelper


@pytest.fixture
def helper():
    return ConverterTestHelper()
