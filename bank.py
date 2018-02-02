# This file is part of Tryton.  The COPYRIGHT file at the top level of this
# repository contains the full copyright notices and license terms.
from trytond.pool import PoolMeta
from trytond.model import fields

__all__ = ['BankAccount']


class BankAccount:
    __metaclass__ = PoolMeta
    __name__ = 'bank.account'
    account = fields.Many2One('account.account', 'Account')
