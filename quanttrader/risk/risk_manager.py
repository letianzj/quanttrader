#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .risk_manager_base import RiskManagerBase
import logging

_logger = logging.getLogger(__name__)


class PassThroughRiskManager(RiskManagerBase):
    def order_in_compliance(self, o, strategy_manager=None):
        """
        Pass through the order without constraints
        :param original_order:
        :param env: e.g. strategy_manager that stores order info vs config info
        :return:
        """
        return True


class RiskManager(RiskManagerBase):
    def order_in_compliance(self, o, strategy_manager=None):
        """
        :param original_order:
        :param env: straegy_manager
        :return:
        """
        # 1. check time str hh:mm:ss
        if 'order_start_time' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['order_start_time'] is not None:
                if o.create_time < strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['order_start_time']:
                    _logger.error(f"Order start time breach {o.source}: {o.create_time} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['order_start_time']}")
                    return False
        if 'order_end_time' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if not strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['order_end_time'] is None:
                if o.create_time > strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['order_end_time']:
                    _logger.error(f"Order end time breach {o.source}: {o.create_time} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['order_end_time']}")
                    return False

        # 2. single trade limit; integer
        if 'single_trade_limit' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if not strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['single_trade_limit'] is None:
                if abs(o.order_size) > strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['single_trade_limit']:
                    _logger.error(f"Order single trade limit breach {o.source}: {o.order_size} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['single_trade_limit']}")
                    return False

        # total # of trades
        if 'total_trade_limit' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if not  strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_trade_limit'] is None:
                a = len(strategy_manager._strategy_dict[o.source]._order_manager.order_dict) - len(strategy_manager._strategy_dict[o.source]._order_manager.canceled_order_set)
                if a > strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_trade_limit']:
                    _logger.error(f"Order total trade limit breach {o.source}: {a} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_trade_limit']}")
                    return False
        if 'total_trade_limit' in strategy_manager._config.keys():
            if not strategy_manager._config['total_trade_limit'] is None:
                a = len(strategy_manager._order_manager.order_dict) - len(strategy_manager._order_manager.canceled_order_set)
                if a > strategy_manager._config['total_trade_limit']:
                    _logger.error(f"Order global total trade limit breach {o.source}: {a} / {strategy_manager._config['total_trade_limit']}")
                    return False

        # cancel # limit
        if 'total_cancel_limit' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if not strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_cancel_limit'] is None:
                a = len(strategy_manager._strategy_dict[o.source]._order_manager.canceled_order_set)
                if a > strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_cancel_limit']:
                    _logger.error(f"Order total cancel limit breach {o.source}: {a} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_cancel_limit']}")
                    return False
        if 'total_cancel_limit' in strategy_manager._config.keys():
            if not strategy_manager._config['total_cancel_limit'] is None:
                a = len(strategy_manager._order_manager.canceled_order_set)
                if a > strategy_manager._config['total_cancel_limit']:
                    _logger.error(f"Order global total cancel limit breach {o.source}: {a} / {strategy_manager._config['total_cancel_limit']}")
                    return False

        # active order # limit
        if 'total_active_limit' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if not strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_active_limit'] is None:
                a = len(strategy_manager._strategy_dict[o.source]._order_manager.standing_order_set)
                if a > strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_active_limit']:
                    _logger.error(f"Order total active limit breach {o.source}: {a} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_active_limit']}")
                    return False
        if 'total_active_limit' in strategy_manager._config.keys():
            if not strategy_manager._config['total_active_limit'] is None:
                a = len(strategy_manager._order_manager.standing_order_set)
                if a > strategy_manager._config['total_active_limit']:
                    _logger.error(f"Order global total active limit breach {o.source}: {a} / {strategy_manager._config['total_active_limit']}")
                    return False

        # pnl
        if 'total_loss_limit' in strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name].keys():
            if not strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_loss_limit'] is None:
                a = strategy_manager._strategy_dict[o.source]._position_manager.get_total_pnl() * (-1.0)
                if a > strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_loss_limit']:
                    _logger.error(f"Order total pnl limit breach {o.source}: {a} / {strategy_manager._config['strategy'][strategy_manager._strategy_dict[o.source].name]['total_loss_limit']}")
                    return False
        if 'total_loss_limit' in strategy_manager._config.keys():
            if not strategy_manager._config['total_loss_limit'] is None:
                a = strategy_manager._position_manager.get_total_pnl() * (-1.0)
                if a > strategy_manager._config['total_loss_limit']:
                    _logger.error(f"Order global total pnl limit breach {o.source}: {a} / {strategy_manager._config['total_loss_limit']}")
                    return False

        # TODO check position, or risk reach; maybe not here but periodic check
        return True
