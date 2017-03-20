# -*- coding: utf-8 -*-

from trytond.pool import PoolMeta
from trytond.model import fields


__all__ = ['BankAccount']


class BankAccount:
    __metaclass__ = PoolMeta
    __name__ = 'bank.account'

    account = fields.Many2One('account.account', 'Account')
