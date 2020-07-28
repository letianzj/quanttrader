"""
quanttrading2.curves.py
~~~~~~~~~~~~~~~~

This exaple module contains classes that model economic supply and
demand curves and compute values such as equilibrium prices. 

It also serves as a demonstration for using type annotations and
abstract base classes in developing libraries intended for use in other
projects.
"""

import abc
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, TypeVar

import numpy as np  # type: ignore


class SupplyCurve:
    """Class for representing supply curves.

    The curves are boostrapped from a set of input points and assumed
    to be piecewise constant

    :param data: Price-Quantity input data points - a collection of dicts
        containing `price` and `supply` keys.
    :type data: Sequence[Dict[str, int]]
    :raises ValueError: if zero price data is encountered.
    :raises SupplyMonotonicityError: when supply data is non-decreasing
        in price.
    """

    def __init__(self, data: Sequence[Dict[str, int]]) -> None:
        data_price_ord = sorted(data, key=lambda e: e['price'])

        if data_price_ord[0]['price'] == 0:
            raise ValueError('invalid price of 0 in supply data')

        for n, e in enumerate(data_price_ord[1:]):
            current_point = e['supply']
            previous_point = data_price_ord[n]['supply']
            if current_point < previous_point:
                raise SupplyMonotonicityError

        self._price = np.array([d['price'] for d in data_price_ord])
        self._quantity = np.array([d['supply'] for d in data_price_ord])
        self._min_price = self._price.min()

    def __eq__(self, other) -> bool:
        if (np.all(self._price == other._price)
                and np.all(self._quantity == other._quantity)):
            return True
        else:
            return False

    def quantity(self, price: float) -> float:
        """Return supply quantity for a given price.

        :param price: Price.
        :type price: float
        :return: Quantity.
        :rtype: float
        """

        if price < self._min_price:
            quantity_at_price = 0.
        else:
            quantity_at_price = self._quantity[self._price <= price][-1]
        return quantity_at_price


class DemandCurve:
    """Class for representing demand curves.

    The curves are boostrapped from a set of input points and assumed
    to be piecewise constant

    :param data: Price-Quantity input data points - a collection of dicts
        containing `price` and `demand` keys.
    :type data: Sequence[Dict[str, int]]
    :raises ValueError: if zero price data is encountered.
    :raises DemandMonotonicityError: When demand data in non-increasing
        in price.
    """

    def __init__(self, data: Sequence[Dict[str, int]]) -> None:
        data_price_ord = sorted(data, key=lambda e: e['price'])

        if data_price_ord[0]['price'] == 0:
            raise ValueError('invalid price of 0 in demand data')

        for n, e in enumerate(data_price_ord[1:]):
            current_point = e['demand']
            previous_point = data_price_ord[n]['demand']
            if current_point > previous_point:
                raise DemandMonotonicityError

        self._price = np.array([d['price'] for d in data_price_ord])
        self._quantity = np.array([d['demand'] for d in data_price_ord])
        self._max_price = self._price.max()

    def __eq__(self, other) -> bool:
        if (np.all(self._price == other._price)
                and np.all(self._quantity == other._quantity)):
            return True
        else:
            return False

    def quantity(self, price: float) -> float:
        """Return demand quantity for a given price.

        :param price: Price.
        :type price: float
        :return: Quantity.
        :rtype: float
        """

        if price > self._max_price:
            quantity_at_price = 0.
        else:
            quantity_at_price = self._quantity[self._price >= price][0]
        return quantity_at_price


class SupplyMonotonicityError(Exception):
    """Exception for non-increasing supply curves."""

    def __init__(self):
        message = 'supply curve not monotonically increasing (by price)'
        super().__init__(message)


class DemandMonotonicityError(Exception):
    """Exception for non-decreasing demand curves."""

    def __init__(self):
        message = 'demand curve not monotonically decreasing (by price)'
        super().__init__(message)


def equil_price(s: SupplyCurve, d: DemandCurve) -> Optional[float]:
    """Computes nearest equilibrium price.

    Searching from below, this function returns the price that is the
    closest to that at which supply equals demand (i.e. the
    equilibrium price).

    :param s: Supply curve.
    :type s: SupplyCurve
    :param d: Demand curve.
    :type d: DemandCurve
    :return: Equilibrium price (if there is one).
    :rtype: Optional[float]
    """

    price_domain = np.unique(np.hstack([np.zeros(1), s._price, d._price]))
    demand_gte_supply = [d.quantity(p) >= s.quantity(p) for p in price_domain]
    if any(demand_gte_supply):
        return price_domain[demand_gte_supply].max()
    else:
        return None


@dataclass(frozen=True)
class PriceRanges:
    """Dataclass for equilibrium price ranges."""

    supply: Tuple[Optional[float], Optional[float]]
    demand: Tuple[Optional[float], Optional[float]]


def equil_price_ranges(s: SupplyCurve, d: DemandCurve) -> PriceRanges:
    """Computes the equilibrium price ranges.

    Searching from below, this function returns the price range that
    includes the point where supply equals demand (i.e. the equilibrium
    price). There is a distinct non-overlapping range for supply and
    demand curves, which approach the equilibrium price from below and
    above, respectively.

    :param s: Supply curve.
    :type s: SupplyCurve
    :param d: Demand curve.
    :type d: DemandCurve
    :return: Equilibrium price range.
    :rtype: PriceRanges
    """

    price_domain = np.unique(np.hstack([np.zeros(1), s._price, d._price]))
    equilibrium = equil_price(s, d)
    if equilibrium:
        prices_below_equil = price_domain[price_domain < equilibrium]
        if len(prices_below_equil) > 0:
            supply_range = (prices_below_equil[-1], equilibrium)
        else:
            supply_range = (None, equilibrium)

        prices_above_equil = price_domain[price_domain > equilibrium]
        if len(prices_above_equil) > 0:
            demand_range = (equilibrium, prices_above_equil[0])
        else:
            demand_range = (equilibrium, None)

        return PriceRanges(supply_range, demand_range)

    else:
        return PriceRanges((None, None), (None, None))


Curve = TypeVar('Curve', SupplyCurve, DemandCurve)
"""Generic type alias for a single curve type"""


class Equilibrium:
    """Class to store the attributes of a supply-demand equilibrium.

    :param s: Supply curve.
    :type s: SupplyCurve
    :param d: Demand curve.
    :type d: DemandCurve
    :param supply_shock: Horizontal supply shock (price).
    :type supply_shock: float
    :param demand_shock: Horizontal demand shock (price).
    :type demand_shock: float
    """

    price: Optional[float]
    price_ranges: PriceRanges
    supply_q: Optional[float]
    demand_q: Optional[float]

    def __init__(self, supply_curve: SupplyCurve,
                 demand_curve: DemandCurve) -> None:
        eq_price_ranges = equil_price_ranges(supply_curve, demand_curve)
        eq_price = eq_price_ranges.demand[0]
        self.price = eq_price
        self.price_ranges = eq_price_ranges
        self.supply_q = supply_curve.quantity(eq_price) if eq_price else None
        self.demand_q = demand_curve.quantity(eq_price) if eq_price else None

    def __eq__(self, other) -> bool:
        criteria = ((self.price == other.price)
                    and (self.supply_q == other.supply_q)
                    and (self.demand_q == other.demand_q))
        if criteria:
            return True
        else:
            return False


class EconShockScenario(metaclass=abc.ABCMeta):
    """Abstract class for representing economic shock scenarios.

    Each instance represents a single economic shock, as measure by the
    impact of the shock on the supply and/or demand curves for a
    product.

    :param supply_shock: Size of shock to apply to supply curves,
        defaults to 0.
    :type supply_shock: float
    :param demand_shock: Size of shock to apply to demand curves,
        defaults to 0.
    :type demand_shock: float
    """

    supply_shock: float
    demand_shock: float

    def __init__(self, supply_shock: float = 0,
                 demand_shock: float = 0) -> None:
        self.supply_shock = supply_shock
        self.demand_shock = demand_shock

    def __repr__(self) -> str:
            class_name = type(self).__name__
            ss = self.supply_shock
            ds = self.demand_shock
            return f'{class_name}(supply_shock={ss}, demand_shock={ds})'

    @abc.abstractmethod
    def apply(self, curve: Curve) -> Curve:
        """Apply economic shock scenario to a supply/demand curve.

        :param curve: Supply or demand curve.
        :type curve: Curve
        :raises TypeError: if curve is not SupplyCurve or DemandCurve
        :return: The supply or demand curve after the economic shock
            scenario has bee applied.
        :rtype: Curve
        """

        pass


class NoneShock(EconShockScenario):
    """Class to represent no economic shock"""

    def apply(self, curve: Curve) -> Curve:
        return curve


none_shock = NoneShock()


class HorizPriceShock(EconShockScenario):
    """Horizontal price shocks (tranlations to supply/demand curves)."""

    def apply(self, curve: Curve) -> Curve:
        if isinstance(curve, SupplyCurve):
            return SupplyCurve(
                [{'price': price + self.supply_shock, 'supply': quantity}
                 for price, quantity in zip(curve._price, curve._quantity)])
        elif isinstance(curve, DemandCurve):
            return DemandCurve(
                [{'price': price + self.demand_shock, 'demand': quantity}
                 for price, quantity in zip(curve._price, curve._quantity)])
        else:
            raise TypeError('curve is not one of SupplyCurve or DemandCurve')
