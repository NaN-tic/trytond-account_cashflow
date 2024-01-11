# -*- coding: utf-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of this
# repository contains the full copyright notices and license terms.
from datetime import timedelta
from sql.aggregate import Sum
from sql import Window
from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import If, Eval, PYSONEncoder
from trytond.wizard import (Wizard, StateView, StateAction, StateTransition,
    Button)
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond import backend


__all__ = ['CashFlowMove', 'CashFlowUpdateCalculate', 'CashFlowUpdate',
    'CashFlowLineForecastContext', 'CashFlowLineForecast']


class CashFlowMove(ModelSQL, ModelView):
    'Cash Flow Move'
    __name__ = 'account.cashflow.move'
    issue_date = fields.Date('Date', required=True)
    planned_date = fields.Date('Planned Date', required=True)
    description = fields.Char('Description')
    bank_account = fields.Many2One('account.account', 'Bank Account')
    amount = fields.Numeric('Amount', required=True, digits=(16, 2))
    party_required = fields.Function(fields.Boolean('Party Required'),
        'get_party_required')
    party = fields.Many2One('party.party', 'Party',
        states={
            'invisible': ~Eval('party_required', False),
        },
        context={
            'company': Eval('company', -1),
            },
        depends=['company'])
    account = fields.Many2One('account.account', 'Account', domain=[
            ('company', '=', Eval('company', -1)),
            ])
    origin = fields.Reference('Origin', selection='get_origin', readonly=True)
    system_computed = fields.Boolean('System Computed', readonly=True,
        help='Record computed by system')
    company = fields.Many2One('company.company', 'Company', required=True)
    planned_date_less_today = fields.Function(
        fields.Boolean('Planned Date Less Today'), 'get_planned_date_less_today')

    @classmethod
    def __setup__(cls):
        super(CashFlowMove, cls).__setup__()
        cls._order = [
            ('planned_date', 'DESC'),
            ('id', 'DESC'),
            ]

    @classmethod
    def __register__(cls, module_name):
        table = cls.__table_handler__(module_name)

        # rename managed into system_computed
        if (table.column_exist('managed')
                and not table.column_exist('system_computed')):
            table.column_rename('managed', 'system_computed')
        super(CashFlowMove, cls).__register__(module_name)

    @staticmethod
    def default_issue_date():
        return Pool().get('ir.date').today()

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @classmethod
    def _get_origin(cls):
        return ['account.move.line']

    @classmethod
    def get_origin(cls):
        pool = Pool()
        Model = pool.get('ir.model')
        models = cls._get_origin()
        models = Model.search([
            ('model', 'in', models)])
        return [('', '')] + [(m.model, m.name) for m in models]

    @classmethod
    def get_party_required(cls, cashes, name):
        res = dict((x.id, False) for x in cashes)
        for cash in cashes:
            res[cash.id] = cash.account.party_required if cash.account else False
        return res

    @classmethod
    def get_planned_date_less_today(cls, cashes, name):
        # PYSON LESS Date https://bugs.tryton.org/issue4879
        Date = Pool().get('ir.date')
        today = Date().today()
        res = dict((x.id, False) for x in cashes)
        for cash in cashes:
            res[cash.id] = cash.planned_date < today
        return res

    @classmethod
    def view_attributes(cls):
        return [
            ('/tree', 'visual', If(Eval('planned_date_less_today'), 'danger', '')),
            ]

    @classmethod
    def copy(cls, moves, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('system_computed', False)
        return super().copy(moves, default)


class CashFlowUpdateCalculate(ModelView):
    'Cash Flow Update'
    __name__ = 'account.cashflow.move.update.start'
    date = fields.Date('Date')
    invoices = fields.Boolean('Invoices')

    @staticmethod
    def default_date():
        return Pool().get('ir.date').today()

    @staticmethod
    def default_invoices():
        return True


class CashFlowUpdate(Wizard):
    'Cash Flow Update'
    __name__ = 'account.cashflow.move.update'
    start = StateView(
        'account.cashflow.move.update.start',
        'account_cashflow.move_update_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Calculate', 'calculate', 'tryton-ok', default=True),
        ])
    calculate = StateTransition()
    open_ = StateAction('account_cashflow.act_cash_move_reports_form')

    def transition_calculate(self):
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        CashFlowMove = pool.get('account.cashflow.move')
        Account = pool.get('account.account')
        BankAccount = pool.get('bank.account')

        CashFlowMove.delete(CashFlowMove.search([
                    ('system_computed', '=', True),
                    ]))

        bank_accounts_ids = [bank_account.account.id
            for bank_account in BankAccount.search([('account', '!=', None)])]
        with Transaction().set_context():
            accounts = Account.search([('id', 'in', bank_accounts_ids)])

        moves = []

        for account in accounts:
            move = CashFlowMove()
            move.issue_date = self.start.date - timedelta(days=1)
            move.planned_date = self.start.date - timedelta(days=1)
            move.bank_account = account
            move.amount = account.balance
            move.system_computed = True
            move.company = account.company
            moves.append(move)

        for line in MoveLine.search(
                [('maturity_date', '>=', self.start.date)]):
            move = CashFlowMove()
            move.issue_date = line.date
            move.planned_date = line.maturity_date
            move.description = line.description
            move.bank_account = (line.bank_account.account if line.bank_account
                else None)
            move.amount = line.debit - line.credit
            move.party = line.party
            move.party_required = line.party_required
            move.account = line.account
            move.origin = line
            move.system_computed = True
            move.company = line.move.company
            moves.append(move)

        CashFlowMove.save(moves)
        self.cash_flow_moves = moves
        return 'open_'

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [x.id for x in self.cash_flow_moves]),
                ])
        return action, {}


class CashFlowLineForecastContext(ModelView):
    'Cash Flow Line Forecast Context'
    __name__ = 'account.cashflow.line.forecast.context'
    cumulate_by_bank_account = fields.Boolean('Cumulate by Bank Account')


class CashFlowLineForecast(ModelSQL, ModelView):
    'Cash Flow Line Forecast'
    __name__ = 'account.cashflow.line.forecast'
    planned_date = fields.Date('Planned Date')
    issue_date = fields.Date('Date')
    description = fields.Char('Description')
    bank_account = fields.Many2One('account.account', 'Bank Account')
    party = fields.Many2One('party.party', "Party",
        context={
            'company': Eval('company', -1),
            },
        depends=['company'])
    account = fields.Many2One('account.account', 'Account')
    origin = fields.Reference('Origin', selection='get_origin', readonly=True)
    system_computed = fields.Boolean('System Computed')
    amount = fields.Numeric('Amount', digits=(16, 2))
    balance = fields.Numeric('Balance', digits=(16, 2))
    company = fields.Many2One('company.company', 'Company', required=True,
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ])

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @classmethod
    def __setup__(cls):
        super(CashFlowLineForecast, cls).__setup__()
        cls._order.insert(0, ('planned_date', 'ASC'))

    @classmethod
    def __register__(cls, module_name):
        table = cls.__table_handler__(module_name)

        # rename managed into system_computed
        if (table.column_exist('managed')
                and not table.column_exist('system_computed')):
            table.column_rename('managed', 'system_computed')
        super(CashFlowLineForecast, cls).__register__(module_name)

    @classmethod
    def _get_origin(cls):
        return ['account.move.line']

    @classmethod
    def get_origin(cls):
        pool = Pool()
        Model = pool.get('ir.model')
        models = cls._get_origin()
        models = Model.search([
            ('model', 'in', models)])
        return [('', '')] + [(m.model, m.name) for m in models]

    @classmethod
    def table_query(cls):
        pool = Pool()
        User = pool.get('res.user')
        user_id = Transaction().user
        user = User(user_id)
        if user.company:
            company_id = Transaction().context.get('company', user.company.id)
        else:
            company_id = None

        CashFlowMove = pool.get('account.cashflow.move')
        cash_flow_move_table = CashFlowMove.__table__()

        context = Transaction().context
        if backend.name == 'postgresql':
            w_columns = []
            if (context.get('cumulate_by_bank_account', False)):
                w_columns.append(cash_flow_move_table.bank_account)
            column_cumulate_by_account = Sum(cash_flow_move_table.amount,
                window=Window(w_columns,
                    order_by=[
                        cash_flow_move_table.planned_date.asc,
                        cash_flow_move_table.id])).as_('balance')
        else:
            column_cumulate_by_account = cash_flow_move_table.amount.as_('balance')

        columns = [
            cash_flow_move_table.id,
            cash_flow_move_table.write_uid,
            cash_flow_move_table.create_uid,
            cash_flow_move_table.write_date,
            cash_flow_move_table.create_date,
            cash_flow_move_table.issue_date.as_('issue_date'),
            cash_flow_move_table.planned_date.as_('planned_date'),
            cash_flow_move_table.company,
            cash_flow_move_table.description.as_('description'),
            cash_flow_move_table.bank_account.as_('bank_account'),
            cash_flow_move_table.party.as_('party'),
            cash_flow_move_table.amount.as_('amount'),
            cash_flow_move_table.account.as_('account'),
            cash_flow_move_table.origin.as_('origin'),
            cash_flow_move_table.system_computed.as_('system_computed'),
            column_cumulate_by_account
            ]
        select = cash_flow_move_table.select(*columns)
        select.where = cash_flow_move_table.company == company_id
        return select
