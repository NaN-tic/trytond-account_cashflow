# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import bank
from . import cashflow


def register():
    Pool.register(
        bank.BankAccount,
        cashflow.CashFlowMove,
        cashflow.CashFlowUpdateCalculate,
        cashflow.CashFlowLineForecast,
        cashflow.CashFlowLineForecastContext,
        module='account_cashflow', type_='model')
    Pool.register(
        cashflow.CashFlowUpdate,
        module='account_cashflow', type_='wizard')
