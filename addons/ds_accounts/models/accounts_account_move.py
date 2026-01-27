# ds_accounts/models/accounts_move.py
from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError


class DsAccountMove(models.Model):
    # _name = "ds.accounts.account.move"
    _inherit = "account.move"

    @api.model
    def create(self, vals):
        # Assign a sequence-like name if needed
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("accounts.journal.entry") or "New"
            )
        return super().create(vals)

    # @api.model
    # def create_journal_entry(
    #     self, name, amount, trip_type="local", partner_id=None, date=None
    # ):
    #     """
    #     Automatically create a journal entry for a TMS trip
    #     """
    #     if amount <= 0:
    #         raise ValidationError("Amount must be greater than zero")

    #     if not date:
    #         date = fields.Date.today()

    #     # Pick journal based on trip type
    #     journal = self.env["accounts.journal"].search(
    #         [("trip_type", "=", trip_type)], limit=1
    #     )

    #     if not journal:
    #         raise ValidationError(f"No journal configured for trip type: {trip_type}")

    #     # Use default debit/credit accounts from the journal
    #     debit_account = journal.default_trip_debit_account_id
    #     credit_account = journal.default_trip_credit_account_id

    #     if not debit_account or not credit_account:
    #         raise ValidationError(
    #             f"Journal {journal.name} does not have default accounts set"
    #         )

    #     # Create the journal entry
    #     move = self.create(
    #         {
    #             "journal_id": journal.id,
    #             "date": date,
    #             "line_ids": [
    #                 (
    #                     0,
    #                     0,
    #                     {
    #                         "account_id": debit_account.id,
    #                         "debit": amount,
    #                         "credit": 0.0,
    #                         "partner_id": partner_id,
    #                         "name": name,
    #                     },
    #                 ),
    #                 (
    #                     0,
    #                     0,
    #                     {
    #                         "account_id": credit_account.id,
    #                         "debit": 0.0,
    #                         "credit": amount,
    #                         "partner_id": partner_id,
    #                         "name": name,
    #                     },
    #                 ),
    #             ],
    #         }
    #     )

    #     # Post the entry
    #     move.action_post()
    #     return move

    @api.model
    def create_journal_entry(
        self,
        *,
        journal_code=None,
        journal_id=None,
        date=None,
        ref=None,
        lines,
        auto_post=True,
        company_id=None,
    ):
        """
        Journal Entry Creator

        :param journal_code: Optional journal code (e.g. 'SALE', 'MISC')
        :param journal_id: Optional explicit journal ID
        :param date: Entry date
        :param ref: Reference / narration
        :param lines: List of dicts (see example)
        :param auto_post: Auto post entry
        :param company_id: Optional company
        """
        """
        Example lines format:
        self.env["account.move"].create_journal_entry(
            journal_code="SALE",
            ref="Trip Income - LR0001",
            auto_post=False, // draft
            lines=[
                {
                    "account_id": income_account.id,
                    "credit": 5000,
                    "partner_id": customer.id,
                    "name": "Freight Income",
                },
                {
                    "account_id": receivable_account.id,
                    "debit": 5000,
                    "partner_id": customer.id,
                    "name": "Customer Receivable",
                },
            ],
        )
        """

        if not lines or len(lines) < 2:
            raise ValidationError("Journal entry must have at least 2 lines.")

        if not date:
            date = fields.Date.context_today(self)

        # Resolve journal
        if not journal_id:
            domain = []
            if journal_code:
                domain.append(("code", "=", journal_code))
            if company_id:
                domain.append(("company_id", "=", company_id))

            journal = self.env["account.journal"].search(domain, limit=1)
            if not journal:
                raise ValidationError("No journal found.")
        else:
            journal = self.env["account.journal"].browse(journal_id)

        move_lines = []
        total_debit = total_credit = 0.0

        for line in lines:
            debit = line.get("debit", 0.0)
            credit = line.get("credit", 0.0)

            if debit <= 0 and credit <= 0:
                raise ValidationError("Each line must have debit or credit.")

            total_debit += debit
            total_credit += credit

            move_lines.append(
                Command.create(
                    {
                        "account_id": line["account_id"],
                        "partner_id": line.get("partner_id"),
                        "name": line.get("name", ref or "/"),
                        "debit": debit,
                        "credit": credit,
                    }
                )
            )

        if round(total_debit, 2) != round(total_credit, 2):
            raise ValidationError(
                f"Unbalanced Entry: Debit={total_debit}, Credit={total_credit}"
            )

        move = self.create(
            {
                "journal_id": journal.id,
                "date": date,
                "ref": ref,
                "line_ids": move_lines,
                "company_id": journal.company_id.id,
            }
        )

        if auto_post:
            move.action_post()

        return move

    @api.model
    def create_invoice(
        self,
        *,
        partner_id,
        lines,
        move_type="out_invoice",  # out_invoice | in_invoice
        invoice_date=None,
        journal_id=None,
        journal_code=None,
        ref=None,
        currency_id=None,
        auto_post=True,
        company_id=None,
    ):
        """
        Invoice / Bill Creator

        Example lines format:
        self.env["account.move"].create_invoice(
            partner_id=customer.id,
            ref="Trip LR-001",
            auto_post=False, // draft
            lines=[
                {
                    "name": "Freight Charges",
                    "account_id": income_account.id,
                    "quantity": 1,
                    "price_unit": 5000,
                    "tax_ids": [gst_18.id],
                }
            ],
        )
        """

        if not partner_id:
            raise ValidationError("Partner is required.")

        if not lines:
            raise ValidationError("Invoice must have at least one line.")

        invoice_date = invoice_date or fields.Date.context_today(self)

        # Resolve journal
        if not journal_id:
            domain = [
                ("type", "=", "sale" if move_type == "out_invoice" else "purchase")
            ]
            if journal_code:
                domain.append(("code", "=", journal_code))
            if company_id:
                domain.append(("company_id", "=", company_id))

            journal = self.env["account.journal"].search(domain, limit=1)
            if not journal:
                raise ValidationError("No suitable journal found.")
        else:
            journal = self.env["account.journal"].browse(journal_id)

        invoice_lines = []

        for line in lines:
            if not line.get("account_id"):
                raise ValidationError("Invoice line must have account_id.")

            invoice_lines.append(
                Command.create(
                    {
                        "name": line.get("name", "/"),
                        "account_id": line["account_id"],
                        "quantity": line.get("quantity", 1.0),
                        "price_unit": line.get("price_unit", 0.0),
                        "tax_ids": [Command.set(line.get("tax_ids", []))],
                        # "analytic_account_id": line.get("account_id"),
                        "account_id": line.get("account_id"),
                    }
                )
            )

        move_vals = {
            "move_type": move_type,
            "partner_id": partner_id,
            "invoice_date": invoice_date,
            "journal_id": journal.id,
            "ref": ref,
            "line_ids": invoice_lines,
        }

        if currency_id:
            move_vals["currency_id"] = currency_id

        if company_id:
            move_vals["company_id"] = company_id

        invoice = self.create(move_vals)

        if auto_post:
            invoice.action_post()

        return invoice
