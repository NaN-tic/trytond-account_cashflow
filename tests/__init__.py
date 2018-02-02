# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.account_cashflow.tests.test_account_cashflow import suite
except ImportError:
    from .test_account_cashflow import suite

__all__ = ['suite']
