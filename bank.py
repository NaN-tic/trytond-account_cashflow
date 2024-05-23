# This file is part of Tryton.  The COPYRIGHT file at the top level of this
# repository contains the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import ModelSQL, fields
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.transaction import Transaction
from trytond import backend
from sql import Column, Null
from trytond.pyson import Eval

account = fields.Many2One('account.account', 'Account')


class BankAccount(CompanyMultiValueMixin, metaclass=PoolMeta):
    __name__ = 'bank.account'
    account = fields.MultiValue(account)
    accounts = fields.One2Many(
        'bank.account.cashflow', 'bank_account', "Accounts")

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'account'}:
            return pool.get('bank.account.cashflow')
        return super().multivalue_model(field)


class BankAccountCashflow(ModelSQL, CompanyValueMixin):
    "Bank Account Cashflow"
    __name__ = 'bank.account.cashflow'
    bank_account = fields.Many2One(
        'bank.account', "Bank Account", ondelete='CASCADE',
        context={
            'company': Eval('company', -1),
            },
        depends={'company'})
    account = account

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        BankAccount = pool.get('bank.account')
        Account = pool.get('account.account')

        sql_table = cls.__table__()
        bank_account = BankAccount.__table__()
        account = Account.__table__()
        cursor = Transaction().connection.cursor()

        exist = backend.TableHandler.table_exist(cls._table)
        bank_account_exist = backend.TableHandler.table_exist(
            BankAccount._table)

        super(BankAccountCashflow, cls).__register__(module_name)

        # Migrate from 6.8: account to multivalue
        if not exist and bank_account_exist:
            bank_account_table = BankAccount.__table_handler__(module_name)
            if bank_account_table.column_exist('account'):
                columns = ['create_uid', 'create_date',
                    'write_uid', 'write_date',
                    'account']
                query = bank_account.join(account, condition=account.id == bank_account.account).select(
                    *[Column(bank_account, c) for c in columns] + [Column(account, 'company'), Column(bank_account, 'id')],
                    where=bank_account.account != Null)
                cursor.execute(*sql_table.insert(
                        columns=[Column(sql_table, c) for c in columns+['company', 'bank_account']],
                        values=query))
