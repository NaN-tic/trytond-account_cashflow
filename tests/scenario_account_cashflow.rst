=========================
Account Cashflow Scenario
=========================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()
    >>> yesterday = today - relativedelta(days=1)
    >>> tomorrow = today + relativedelta(days=1)

Install account_cashflow::

    >>> config = activate_modules('account_cashflow')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

Create parties::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create Bank Account::

    >>> Bank = Model.get('bank')
    >>> BankAccount = Model.get('bank.account')
    >>> Number = Model.get('bank.account.number')
    >>> Bank = Model.get('bank')
    >>> BankAccount = Model.get('bank.account')
    >>> BankNumber = Model.get('bank.account.number')
    >>> bparty = Party()
    >>> bparty.name = 'Bank'
    >>> bparty.save()
    >>> bank = Bank(party=bparty)
    >>> bank.save()
    >>> bank_account = BankAccount()
    >>> bank_account.bank = bank
    >>> bank_number = bank_account.numbers.new()
    >>> bank_number.type = 'iban'
    >>> bank_number.number = 'BE82068896274468'
    >>> bank_number = bank_account.numbers.new()
    >>> bank_number.type = 'other'
    >>> bank_number.number = 'not IBAN'
    >>> bank_account.account = receivable
    >>> bank_account.save()

Create Moves to reconcile::

    >>> Journal = Model.get('account.journal')
    >>> Move = Model.get('account.move')
    >>> Line = Model.get('account.move.line')
    >>> journal_revenue, = Journal.find([
    ...         ('code', '=', 'REV'),
    ...         ])
    >>> journal_cash, = Journal.find([
    ...         ('code', '=', 'CASH'),
    ...         ])

    >>> move = Move()
    >>> move.period = period
    >>> move.journal = journal_revenue
    >>> move.date = period.start_date
    >>> line = move.lines.new()
    >>> line.account = revenue
    >>> line.credit = Decimal(42)
    >>> line = move.lines.new()
    >>> line.account = receivable
    >>> line.debit = Decimal(42)
    >>> line.party = customer
    >>> line.maturity_date = tomorrow
    >>> move.save()

    >>> move = Move()
    >>> move.period = period
    >>> move.journal = journal_cash
    >>> move.date = period.start_date
    >>> line = move.lines.new()
    >>> line.account = cash
    >>> line.debit = Decimal(40)
    >>> line = move.lines.new()
    >>> line.account = receivable
    >>> line.credit = Decimal(40)
    >>> line.party = customer
    >>> move.save()

Run Cashflow wizard::

    >>> cashflow = Wizard('account.cashflow.move.update')
    >>> cashflow.execute('calculate')

    >>> CashFlowMove = Model.get('account.cashflow.move')
    >>> cflows = CashFlowMove.find([])
    >>> len(cflows) == 2
    True

Cash Flow Forecast::

    >>> CashFlowLineForecast = Model.get('account.cashflow.line.forecast')
    >>> cforecasts = CashFlowLineForecast.find([])
    >>> len(cforecasts) == 2
    True
