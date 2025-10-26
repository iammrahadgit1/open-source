from odoo import models, fields, api

class TTPartnerLedgerWizard(models.TransientModel):
    _name = 'tt.partner.ledger.wizard'
    _description = 'TT Partner Ledger Wizard'

    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
