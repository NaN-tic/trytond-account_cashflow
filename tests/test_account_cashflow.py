# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class TestAccountCashflowCase(ModuleTestCase):
    'Test Account Cashflow module'
    module = 'account_cashflow'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            TestAccountCashflowCase))
    return suite
