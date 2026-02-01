{
    "name": "ds_accounts",
    "summary": "General Accounts & Invoicings",
    "version": "1.0",
    "application": True,
    "author": "Dorii Software",
    "website": "https://www.dorii.in",
    "category": "Uncategorized",
    "depends": ["account", "l10n_in"],
    "data": [
        ## security
        "security/ir.model.access.csv",
        "views/dummy.xml",
        "views/accounts_chart_of_account_views.xml",
        "views/accounts_journal_views.xml",
        "views/accounts_account_move_views.xml",
        "views/accounts_customer_receipt_views.xml",
        # reports
        "views/accounts_cashbook_views.xml",
        # masters
        "views/accounts_party_ledger_views.xml",
        ## data
        # "data/journals.xml",
        # "data/accounts.xml",
        ## sequences
        "data/sequences.xml",
        ##navigation (last)
        "views/navigation.xml",
    ],
    "installable": True,
}
