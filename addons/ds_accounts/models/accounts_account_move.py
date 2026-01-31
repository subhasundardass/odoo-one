# ds_accounts/models/accounts_move.py
from odoo import _, models, fields, api, Command
from odoo.exceptions import ValidationError
import pdb
import logging

_logger = logging.getLogger(__name__)


class DsAccountMove(models.Model):
    # _name = "ds.accounts.account.move"
    _inherit = "account.move"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    unpaid_invoice_ids = fields.Many2many(
        "account.move",
        string="Unpaid Invoices",
        domain="[('partner_id','=',partner_id),('move_type','=','out_invoice'),('payment_state','in',['not_paid','partial'])]",
        compute="_compute_unpaid_invoices",
    )
    receipt_amount = fields.Monetary(
        string="Receipt Amount",
        currency_field="currency_id",
        default=0.0,
        help="Total amount received to apply on unpaid invoices",
    )
    total_due = fields.Monetary(
        string="Total Due",
        currency_field="currency_id",
        compute="_compute_total_due",
        store=False,  # recompute dynamically
    )

    receipt_ref = fields.Char()

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

    @api.depends("unpaid_invoice_ids.amount_residual")
    def _compute_total_due(self):
        for rec in self:
            rec.total_due = sum(inv.amount_residual for inv in rec.unpaid_invoice_ids)

    @api.depends("partner_id")
    def _compute_unpaid_invoices(self):
        for rec in self:
            rec.unpaid_invoice_ids = self.env["account.move"].search(
                [
                    ("partner_id", "=", rec.partner_id.id),
                    ("move_type", "=", "out_invoice"),
                    ("payment_state", "in", ["not_paid", "partial"]),
                    ("amount_residual", "!=", 0.0),
                ],
                order="invoice_date asc",
            )  # FIFO: oldest first

    # def action_post_receipt(self):
    #     for rec in self:
    #         # 1️⃣ Validate partner and receipt amount
    #         if not rec.partner_id:
    #             raise ValidationError(
    #                 "Please select a customer before posting the receipt."
    #             )
    #         if not rec.receipt_amount or rec.receipt_amount <= 0:
    #             raise ValidationError("Please enter a valid receipt amount.")

    #         # 2️⃣ Ensure journal is set
    #         if not rec.journal_id:
    #             journal = self.env["account.journal"].search(
    #                 [
    #                     ("type", "in", ("bank", "cash")),
    #                     ("company_id", "=", rec.company_id.id),
    #                 ],
    #                 limit=1,
    #             )
    #             if not journal:
    #                 raise ValidationError(
    #                     "Please configure a bank/cash journal for this company."
    #                 )
    #             rec.journal_id = journal
    #         else:
    #             journal = rec.journal_id

    #         # 3️⃣ Apply payment to unpaid invoices (FIFO)
    #         amount_to_apply = rec.receipt_amount
    #         unpaid_invoices = rec.unpaid_invoice_ids
    #         if not unpaid_invoices:
    #             raise ValidationError("No unpaid invoices found for this partner.")

    #         for inv in unpaid_invoices:
    #             if amount_to_apply <= 0:
    #                 break
    #             pay_amount = min(amount_to_apply, inv.amount_residual)

    #             # Use Command to create payment lines
    #             inv.write(
    #                 {
    #                     "line_ids": [
    #                         Command.create(
    #                             {
    #                                 "account_id": inv.account_id.id,
    #                                 "partner_id": rec.partner_id.id,
    #                                 "debit": (
    #                                     pay_amount
    #                                     if inv.move_type == "in_invoice"
    #                                     else 0.0
    #                                 ),
    #                                 "credit": (
    #                                     pay_amount
    #                                     if inv.move_type == "out_invoice"
    #                                     else 0.0
    #                                 ),
    #                                 "name": f"Payment applied from {rec.name}",
    #                             }
    #                         )
    #                     ]
    #                 }
    #             )
    #             amount_to_apply -= pay_amount

    #         # 4️⃣ Handle overpayment
    #         if amount_to_apply > 0:
    #             vals = {
    #                 "journal_id": journal.id,
    #                 "date": rec.date,
    #                 "ref": f"Advance payment for {rec.partner_id.name}",
    #                 "line_ids": [
    #                     Command.create(
    #                         {
    #                             "account_id": self.env.ref(
    #                                 "account.account_receivable"
    #                             ).id,
    #                             "debit": amount_to_apply,
    #                             "partner_id": rec.partner_id.id,
    #                             "name": "Advance Payment",
    #                         }
    #                     ),
    #                     Command.create(
    #                         {
    #                             "account_id": journal.default_credit_account_id.id,
    #                             "credit": amount_to_apply,
    #                             "partner_id": rec.partner_id.id,
    #                             "name": "Advance Payment",
    #                         }
    #                     ),
    #                 ],
    #             }
    #             account_move = self.env["account.move"].create(vals)
    #             account_move.action_post()

    #         rec.action_post()

    def action_receive_customer_payment(self, amount=None):
        self.ensure_one()
        move = self

        # -------------------------------------------------
        # 1️⃣ VALIDATION
        # -------------------------------------------------
        if move.move_type != "out_invoice":
            raise ValidationError(_("Only customer invoices allowed."))

        if move.state != "posted":
            raise ValidationError(_("Invoice must be posted."))

        amount = amount or move.amount_residual
        if amount <= 0:
            raise ValidationError(_("Nothing to receive."))

        journal = self.env["account.journal"].search(
            [
                ("type", "in", ("bank", "cash")),
                ("company_id", "=", move.company_id.id),
            ],
            limit=1,
        )
        if not journal:
            raise ValidationError(_("Configure a Bank/Cash journal."))

        if not move.partner_id.property_account_receivable_id:
            raise ValidationError(_("Customer receivable account missing."))

        # -------------------------------------------------
        # 2️⃣ PAYMENT METHOD
        # -------------------------------------------------
        payment_method_line = journal.inbound_payment_method_line_ids[:1]
        if not payment_method_line:
            raise ValidationError(
                _("No inbound payment method configured on journal %s.")
                % journal.display_name
            )

        # -------------------------------------------------
        # 3️⃣ CREATE PAYMENT
        # -------------------------------------------------
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": move.partner_id.id,
                "amount": amount,
                "journal_id": journal.id,
                "payment_method_line_id": payment_method_line.id,
                "date": fields.Date.context_today(self),
                "company_id": move.company_id.id,
                "ref": _("Receipt for %s") % move.name,
            }
        )

        # THIS WILL NOW WORK
        # payment.action_post()

        # -------------------------------------------------
        # 4️⃣ FIFO RECONCILIATION
        # -------------------------------------------------
        # unpaid_invoices = self.env["account.move"].search(
        #     [
        #         ("partner_id", "=", move.partner_id.id),
        #         ("move_type", "=", "out_invoice"),
        #         ("state", "=", "posted"),
        #         ("payment_state", "in", ("not_paid", "partial")),
        #         ("company_id", "=", move.company_id.id),
        #     ],
        #     order="invoice_date asc, id asc",
        # )

        # receivable = move.partner_id.property_account_receivable_id

        # payment_lines = payment.line_ids.filtered(
        #     lambda l: l.account_id == receivable and not l.reconciled
        # )

        # for inv in unpaid_invoices:
        #     if not payment_lines:
        #         break

        #     inv_lines = inv.line_ids.filtered(
        #         lambda l: l.account_id == receivable and not l.reconciled
        #     )

        #     (payment_lines + inv_lines).reconcile()

        #     payment_lines = payment.line_ids.filtered(
        #         lambda l: l.account_id == receivable and not l.reconciled
        #     )

        return payment
