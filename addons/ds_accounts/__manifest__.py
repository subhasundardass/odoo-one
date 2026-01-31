{
    "name": "ds_accounts",
    "summary": "General Accounts & Invoicings - Dorii Software",
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
        "views/accounts_party_ledger_views.xml",
        # --invoices
        "views/accounts_customer_invoice_views.xml",
        # --operations
        "views/accounts_receipt_views.xml",
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
