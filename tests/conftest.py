"""

tests.conftest.py
~~~~~~~~~~~~~~~~~

This module is used by PyTest to detect test fixtures that are used by
multiple test modules. For more imformation on fixtures in PyTest, see
https://docs.pytest.org/en/latest/fixture.html.
"""

import json
from typing import Any, Dict, List

import pytest

from quanttrading2.curves import SupplyCurve, DemandCurve


def load_test_data() -> List[Dict[str, Any]]:
    """Load test data from JSON file.

    :return: Test data.
    :rtype: Dict[str, Any]
    """

    config_file_path = 'tests/test_data/supply_demand_data.json'
    with open(config_file_path) as file:
        json_data = file.read()

    data = json.loads(json_data)
    return data['supply_demand']


@pytest.fixture
def supply_curve() -> SupplyCurve:
    """Return a supply curve for use with tests.

    :return: A Supply curve.
    :rtype: SupplyCurve
    """

    supply_demand_data = load_test_data()
    return SupplyCurve(supply_demand_data)


@pytest.fixture
def demand_curve() -> DemandCurve:
    """Return a demand curve for use with tests.

    :return: A demand curve.
    :rtype: DemandCurve
    """

    supply_demand_data = load_test_data()
    return DemandCurve(supply_demand_data)
