# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from odoo.tools.misc import format_date

import logging

_logger = logging.getLogger(__name__)


class ReportAccountAgedPartnerCustomize(models.AbstractModel):
    _inherit = "account.aged.partner"

    order_no = fields.Char(group_operator='max')
    currency_rate = fields.Float(group_operator='max')

    amount_paid = fields.Monetary(currency_field='currency_id')
    amount_residual = fields.Monetary(currency_field='currency_id')

    balance = fields.Monetary()
    part_debit_amount = fields.Monetary()
    part_credit_amount = fields.Monetary()
    amount_check = fields.Float()

    @api.model
    def _get_sql(self):
        options = self.env.context['report_options']
        query = ("""
                SELECT
                    {move_line_fields},
                    account_move_line.amount_currency as amount_currency,
                    account_move_line.partner_id AS partner_id,
                    partner.name AS partner_name,
                    COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                    COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                    account_move_line.payment_id AS payment_id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                    account_move_line.expected_pay_date AS expected_pay_date,
                    move.move_type AS move_type,
                    move.name AS move_name,
                    move.ref AS move_ref,
                    
                    COALESCE(SUM(part_debit.amount_currency), 0) AS amount_paid,
                    (account_move_line.amount_currency - COALESCE(SUM(part_debit.amount_currency), 0)) AS amount_residual,
                    
                    COALESCE(SUM(part_debit.amount), 0) AS part_debit_amount,
                    COALESCE(SUM(part_credit.amount), 0) AS part_credit_amount,
                    
                    ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), currency_table.precision) AS amount_check,
                    
                    COALESCE(so.name, move.ref) AS order_no,
                    curr_rate.rate AS currency_rate,
                    
                    account.code || ' ' || account.name AS account_name,
                    account.code AS account_code,""" + ','.join([("""
                    CASE WHEN period_table.period_index = {i}
                    THEN %(sign)s * ROUND((
                        CASE WHEN curr_rate.rate > 0
                        THEN (account_move_line.amount_currency/curr_rate.rate - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0))
                        ELSE (account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0))
                        END
                    ) * currency_table.rate, currency_table.precision)
                    ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
                FROM account_move_line
                JOIN account_move move ON account_move_line.move_id = move.id
                LEFT JOIN sale_order so ON move.x_studio_source_order = so.id
                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_account account ON account.id = account_move_line.account_id
                LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN ir_property trust_property ON (
                    trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                    AND trust_property.name = 'trust'
                    AND trust_property.company_id = account_move_line.company_id
                )
                JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN LATERAL (
                    SELECT cr_c1.currency_id, cr_c1.rate
                    FROM res_currency_rate cr_c1
                    WHERE cr_c1.currency_id = account_move_line.currency_id
                    AND cr_c1.name <= %(date)s
                    ORDER BY cr_c1.name DESC 
                    LIMIT 1
                ) curr_rate ON account_move_line.currency_id = curr_rate.currency_id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.debit_move_id, part.debit_amount_currency AS amount_currency
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date)s
                ) part_debit ON part_debit.debit_move_id = account_move_line.id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.credit_move_id
                    FROM account_partial_reconcile part
                    WHERE part.max_date <= %(date)s
                ) part_credit ON part_credit.credit_move_id = account_move_line.id
                JOIN {period_table} ON (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                )
                WHERE account.internal_type = %(account_type)s
                AND account.exclude_from_aged_reports IS NOT TRUE
                GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                         period_table.period_index, currency_table.rate, currency_table.precision, 
                         so.id,
                         curr_rate.rate
                HAVING ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), currency_table.precision) != 0
            """).format(
            move_line_fields=self._get_move_line_fields('account_move_line'),
            currency_table=self.env['res.currency']._get_query_currency_table(options),
            period_table=self._get_query_period_table(options),
        )
        params = {
            'account_type': options['filter_account_type'],
            'sign': 1 if options['filter_account_type'] == 'receivable' else -1,
            'date': options['date']['date_to'],
        }
        return self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)

    @api.model
    def _get_column_details(self, options):
        columns = [
            self._header_column(),
            self._field_column('report_date'),

            # self._field_column('balance', name=_("balance")),
            # self._field_column('part_debit_amount', name=_("part_debit_amount")),
            # self._field_column('part_credit_amount', name=_("part_credit_amount")),
            # self._field_column('amount_check', name=_("amount_check")),

            self._field_column('account_name', name=_("Account")),
            self._field_column('order_no', name=_("Order No.")),

            self._field_column('expected_pay_date'),
            self._field_column('period0', name=_("As of: %s", format_date(self.env, options['date']['date_to']))),
            self._field_column('period1', sortable=True),
            self._field_column('period2', sortable=True),
            self._field_column('period3', sortable=True),
            self._field_column('period4', sortable=True),
            self._field_column('period5', sortable=True),
            self._custom_column(  # Avoid doing twice the sub-select in the view
                name=_('Total'),
                classes=['number'],
                formatter=self.format_value,
                getter=(
                    lambda v: v['period0'] + v['period1'] + v['period2'] + v['period3'] + v['period4'] + v['period5']),
                sortable=True,
            ),
        ]

        if self.user_has_groups('base.group_multi_currency'):
            columns[2:2] = [
                self._field_column('amount_residual', name=_("Balance in original currency Amount")),
                self._field_column('amount_currency', name=_("Original Invoice Amount")),

                self._field_column('currency_id'),
                self._field_column('currency_rate', name=_("Rate")),

                self._custom_column(  # Avoid doing twice the sub-select in the view
                    name=_('Original Currency Amount'),
                    classes=['number'],
                    formatter=self.format_value,
                    getter=(
                        lambda v: v['amount_currency'] / (v['currency_rate'] or 1)),
                    sortable=True,
                ),
            ]

        return columns


class ReportAccountAgedPayableCustomize(models.Model):
    _inherit = "account.aged.payable"
    _auto = False

    @api.model
    def _get_sql(self):
        options = self.env.context['report_options']
        query = ("""
                        SELECT
                        {move_line_fields},
                        account_move_line.amount_currency as amount_currency,
                        account_move_line.partner_id AS partner_id,
                        partner.name AS partner_name,
                        COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                        COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                        account_move_line.payment_id AS payment_id,
                        COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                        account_move_line.expected_pay_date AS expected_pay_date,
                        move.move_type AS move_type,
                        move.name AS move_name,
                        move.ref AS move_ref,
                        COALESCE(SUM(part_credit.amount_currency), 0) AS amount_paid,
                        (account_move_line.amount_currency + COALESCE(SUM(part_credit.amount_currency), 0)) AS amount_residual,
                        COALESCE(SUM(part_debit.amount), 0) AS part_debit_amount,
                        COALESCE(SUM(part_credit.amount), 0) AS part_credit_amount,
                        
                        ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), 0) AS amount_check,
                        
                        COALESCE(so.name, move.ref) AS order_no,
                        curr_rate.rate AS currency_rate,
                        
                        account.code || ' ' || account.name AS account_name,
                        account.code AS account_code,""" + ','.join([("""
                        CASE WHEN period_table.period_index = {i}
                        THEN %(sign)s * ROUND((
                            CASE WHEN curr_rate.rate > 0
                            THEN (account_move_line.amount_currency - COALESCE(SUM(part_debit.amount_currency), 0) + COALESCE(SUM(part_credit.amount_currency), 0)) / curr_rate.rate
                            ELSE (account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0))
                            END
                        ) * currency_table.rate, currency_table.precision)
                        ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
                    FROM account_move_line
                    JOIN account_move move ON account_move_line.move_id = move.id
                    LEFT JOIN sale_order so ON move.x_studio_source_order = so.id
                    JOIN account_journal journal ON journal.id = account_move_line.journal_id
                    JOIN account_account account ON account.id = account_move_line.account_id
                    LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
                    LEFT JOIN ir_property trust_property ON (
                        trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                        AND trust_property.name = 'trust'
                        AND trust_property.company_id = account_move_line.company_id
                    )
                    JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
                    LEFT JOIN LATERAL (
                        SELECT cr_c1.currency_id, cr_c1.rate
                        FROM res_currency_rate cr_c1
                        WHERE cr_c1.currency_id = account_move_line.currency_id
                        AND cr_c1.name <= %(date)s
                        ORDER BY cr_c1.name DESC 
                        LIMIT 1
                    ) curr_rate ON account_move_line.currency_id = curr_rate.currency_id
                    LEFT JOIN LATERAL (
                        SELECT part.amount, part.debit_move_id, part.debit_amount_currency AS amount_currency
                        FROM account_partial_reconcile part
                        WHERE part.max_date <= %(date)s
                    ) part_debit ON part_debit.debit_move_id = account_move_line.id
                    LEFT JOIN LATERAL (
                        SELECT part.amount, part.credit_move_id, part.debit_amount_currency AS amount_currency
                        FROM account_partial_reconcile part
                        WHERE part.max_date <= %(date)s
                    ) part_credit ON part_credit.credit_move_id = account_move_line.id
                    JOIN {period_table} ON (
                        period_table.date_start IS NULL
                        OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                    )
                    AND (
                        period_table.date_stop IS NULL
                        OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                    )
                    WHERE account.internal_type = %(account_type)s
                    AND account.exclude_from_aged_reports IS NOT TRUE
                    GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                             period_table.period_index, currency_table.rate, currency_table.precision, 
                             so.id,
                             curr_rate.rate
                    HAVING ROUND(account_move_line.amount_currency - COALESCE(SUM(part_debit.amount_currency), 0) + COALESCE(SUM(part_credit.amount_currency), 0), 0) != 0
                """).format(
            move_line_fields=self._get_move_line_fields('account_move_line'),
            currency_table=self.env['res.currency']._get_query_currency_table(options),
            period_table=self._get_query_period_table(options),
        )
        # HAVING ROUND(account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0), 0) != 0
        # HAVING ROUND(account_move_line.amount_currency + COALESCE(SUM(part_credit.amount_currency), 0)) != 0
        params = {
            'account_type': options['filter_account_type'],
            'sign': 1 if options['filter_account_type'] == 'receivable' else -1,
            'date': options['date']['date_to'],
        }
        return self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)
