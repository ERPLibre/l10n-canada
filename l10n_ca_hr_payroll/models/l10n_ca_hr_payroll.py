##############################################################################
#
#    Copyright (C) 2012 Amura Consulting. All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models


class HrPayrollTaxTable(models.Model):
    """
    Canadian Tax Payroll Table
    """
    _name = 'hr.payroll.tax.table'
    _description = 'Canadian Tax Payroll Table'

    def onchange_year(self, cr, uid, ids, year, prov=False):
        res = {}
        res['name'] = 'Tax Table: ' + str(year)
        if prov:
            prov_obj = self.pool.get('res.country.state').browse(cr, uid, prov)
            res['name'] += ' / Provincial - ' + prov_obj.code
        else:
            res['name'] += ' / Federal'

        return {'value': res}

    name = fields.Char('Description', size=128)
    year = fields.Integer('Year', required=True)
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    jurisdiction = fields.Selection(selection=[('federal', 'Federal'),
                                               ('provincial', 'Provincial')], string='Jurisdiction', required=True)
    state_id = fields.Many2one('res.country.state', 'Province')
    type = fields.Selection(selection=[('federal', 'Federal'),
                                       ('ei', 'Employment Insurance'),
                                       ('qc', 'Quebec'),
                                       ('rqap', 'RQAP / RRQ'),
                                       ('csst', 'CSST')], string='Type', required=True)
    line_federal_ids = fields.One2many('hr.payroll.tax.table.federal.line', 'table_id', 'Lines')
    line_ei_ids = fields.One2many('hr.payroll.tax.table.ei.line', 'table_id', 'Lines')
    line_qc_ids = fields.One2many('hr.payroll.tax.table.qc.line', 'table_id', 'Lines')
    line_rqap_ids = fields.One2many('hr.payroll.tax.table.rqap.line', 'table_id', 'Lines')
    line_csst_ids = fields.One2many('hr.payroll.tax.table.csst.line', 'table_id', 'Lines')

    _defaults = {
        'jurisdiction': 'federal',
        'type': 'federal',
    }


class hr_payroll_tax_table_federal_line(models.Model):
    """
    Federal Lines
    """
    _name = 'hr.payroll.tax.table.federal.line'
    _description = 'Federal Lines'
    table_id = fields.Many2one('hr.payroll.tax.table', 'Table')
    inc_from = fields.Float('Income From', digits=(16, 2), required=True)
    name = fields.Char('Income From', compute="_get_inc_from_str", readonly=True, copy=False)
    inc_to = fields.Float('Income To', digits=(16, 2), required=True)
    code0 = fields.Float('Code 0', digits=(16, 2))
    code1 = fields.Float('Code 1', digits=(16, 2))
    code2 = fields.Float('Code 2', digits=(16, 2))
    code3 = fields.Float('Code 3', digits=(16, 2))
    code4 = fields.Float('Code 4', digits=(16, 2))
    code5 = fields.Float('Code 5', digits=(16, 2))
    code6 = fields.Float('Code 6', digits=(16, 2))
    code7 = fields.Float('Code 7', digits=(16, 2))
    code8 = fields.Float('Code 8', digits=(16, 2))
    code9 = fields.Float('Code 9', digits=(16, 2))
    code10 = fields.Float('Code 10', digits=(16, 2))

    def _get_inc_from_str(self):
        for obj in self:
            obj.name = str(obj.inc_from)


class hr_payroll_tax_table_ei_line(models.Model):
    """
    Employment Insurance Lines
    """
    _name = 'hr.payroll.tax.table.ei.line'
    _description = 'Employment Insurance Lines'
    table_id = fields.Many2one('hr.payroll.tax.table', 'Table')
    inc_from = fields.Float('Income From', digits=(16, 2), required=True)
    name = fields.Char('Income From', compute="_get_inc_from_str", readonly=True, copy=False)
    inc_to = fields.Float('Income To', digits=(16, 2), required=True)
    rate = fields.Float('Rate', digits=(16, 2), required=True)
    max_annual_insurable_earnings = fields.Float(
        'Maximum Annual Insurable Earnings',
        digits=(16, 2), required=True,
    )

    def _get_inc_from_str(self):
        for obj in self:
            obj.name = str(obj.inc_from)


class hr_payroll_tax_table_qc_line(models.Model):
    """
    Quebec Lines
    """
    _name = 'hr.payroll.tax.table.qc.line'
    _description = 'Quebec Lines'
    table_id = fields.Many2one('hr.payroll.tax.table', 'Table')
    inc_from = fields.Float('Income From', digits=(16, 2), required=True)
    name = fields.Char('Income From', compute="_get_inc_from_str", readonly=True, copy=False)
    inc_to = fields.Float('Income To', digits=(16, 2), required=True)
    code0 = fields.Float('Code 0', digits=(16, 2))
    codeA = fields.Float('Code A', digits=(16, 2))
    codeB = fields.Float('Code B', digits=(16, 2))
    codeC = fields.Float('Code C', digits=(16, 2))
    codeD = fields.Float('Code D', digits=(16, 2))
    codeE = fields.Float('Code E', digits=(16, 2))
    codeF = fields.Float('Code F', digits=(16, 2))
    codeG = fields.Float('Code G', digits=(16, 2))
    codeH = fields.Float('Code H', digits=(16, 2))
    codeI = fields.Float('Code I', digits=(16, 2))
    codeJ = fields.Float('Code J', digits=(16, 2))
    codeK = fields.Float('Code K', digits=(16, 2))
    codeL = fields.Float('Code L', digits=(16, 2))
    codeM = fields.Float('Code M', digits=(16, 2))
    codeN = fields.Float('Code N', digits=(16, 2))
    codeY = fields.Float('Code Y', digits=(16, 2))
    codeZ = fields.Float('Code Z', digits=(16, 2))

    def _get_inc_from_str(self):
        for obj in self:
            obj.name = str(obj.inc_from)


class hr_payroll_tax_table_rqap_line(models.Model):
    """
    RQAP Lines
    """
    _name = 'hr.payroll.tax.table.rqap.line'
    _description = 'RQAP Lines'
    table_id = fields.Many2one('hr.payroll.tax.table', 'Table')
    inc_from = fields.Float('Income From', digits=(16, 2), required=True)
    inc_to = fields.Float('Income To', digits=(16, 2), required=True)
    employee_contrib = fields.Float('Employee contribution', digits=(16, 2))
    employer_contrib = fields.Float('Employer contribution', digits=(16, 2))
    max_annual_insurable_earnings = fields.Float('Maximum Annual Insurable Earnings', digits=(16, 2))


class hr_payroll_tax_table_csst_line(models.Model):
    """
    CSST Lines
    """
    _name = 'hr.payroll.tax.table.csst.line'
    _description = 'CSST Lines'
    name = fields.Char('Name', size=256, required=True)
    table_id = fields.Many2one('hr.payroll.tax.table', 'Table')


class hr_employee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    ei_exempt = fields.Boolean('EI Exempt')
    td1f = fields.Selection([
        ('code1', '1'),
        ('code2', '2'),
        ('code3', '3'),
        ('code4', '4'),
        ('code5', '5'),
        ('code6', '6'),
        ('code7', '7'),
        ('code8', '8'),
        ('code9', '9'),
        ('code10', '10'),
        ('code0', '0')
    ], 'Federal Claim Code', required=True)
    td1p = fields.Selection([
        ('codeA', 'A'),
        ('codeB', 'B'),
        ('codeC', 'C'),
        ('codeD', 'D'),
        ('codeE', 'E'),
        ('codeF', 'F'),
        ('codeG', 'G'),
        ('codeH', 'H'),
        ('codeI', 'I'),
        ('codeJ', 'J'),
        ('codeK', 'K'),
        ('codeL', 'L'),
        ('codeM', 'M'),
        ('codeN', 'N'),
        ('codeY', 'Y'),
        ('codeZ', 'Z'),
        ('code0', '0')
    ], 'Provincial Claim Code', required=True)
    cpp_exempt = fields.Boolean('CPP/QPP Exempt')
    qpip_exempt = fields.Boolean('QPIP Exempt')
    cpp_ytd_adj = fields.Float('CPP/QPP YTD Adjustment', help="""\
Amount to adjust CPP/QPP for calculations.
Used if employee has contributed elsewhere and will be factored in when
calculating maximum CPP payment""")
    ei_ytd_adj = fields.Float('EI YTD Adjustment', help="""\
Amount to adjust EI for calculations.
Used if employee has contributed elsewhere and will be factored in when
calculating maximum EI payment""")
    vac_pay = fields.Float('Vacation Pay %', digits=(16, 2))
    f1 = fields.Float(name='Childcare/Alimony (F1)', digits=(16, 2), help="""\
Annual deductions such as child care expenses and support payments, etc.,
authorized by a tax services office or tax centre""")
    f2 = fields.Float('Alimony/Maint Garnish (F2)', digits=(16, 2), help="""\
Alimony or maintenance payments required by a legal document to be
payroll-deducted authorized by a tax services office or tax centre""")
    hd = fields.Float('Prescribed Zone (HD)', digits=(16, 2), help="""\
Annual deduction for living in a prescribed zone as indicated on Form TD1""")
    lcf = fields.Float('Fed Labour sponsored funds (LCF)', digits=(16, 2),
                       help="Federal labour-sponsored funds tax credit")
    lcp = fields.Float(
        'Prov Labour sponsored funds (LCP)', digits=(16, 2),
        help="Provincial or territorial labour-sponsored funds tax credit")
    f = fields.Float('RSP/RPP/RCA (F)', digits=(16, 2), help="""
Payroll deductions for employee contributions to a registered pension plan (RPP),
a registered retirement savings plan (RRSP),
or a retirement compensation arrangement (RCA)""")
    l = fields.Float('Extra Tax Deductions (L)', digits=(16, 2),
                     help="Extra tax deductions requested for the pay period.")
    k3 = fields.Float('Federal Medical (K3)', digits=(16, 2), help="""\
Other federal tax credits, such as medical expenses and charitable donations
authorized by a tax services office or tax centre""")
    u1 = fields.Float('Union Dues (U1)', digits=(16, 2), help="Union dues"),
    y = fields.Float('MB/ON Extra Tax Reduction(Y)', digits=(16, 2), help="""\
Extra provincial or territorial tax reduction based on applicable amounts
reported on the provincial or territorial Form TD1""")
    td1 = fields.Float('Personal Tax Credits Return (TD1)', digits=(16, 2),
                       required=True, help="Personal Tax Credits Return")
    eeins = fields.Float('Insurance - Employee Contribution (EeINS)', digits=(16, 2), required=True)
    erins = fields.Float('Insurance - Employer Contribution (ErINS)', digits=(16, 2), required=True)

    _defaults = {
        'td1f': 'code1',
        'td1p': 'codeA',
        'td1': 11038.00,
        'eeins': 0.00,
        'erins': 0.00,
    }


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    def _get_pays_per_year(self, cr, uid, ids, names, arg, context=None):
        """
        @param ids: ID of contract
        @return: The number of pays per year
        """
        res = {}
        # FIXME: Should likely pull these values from somewhere else, depending on whether a 52 or 53 year week is used
        schedule_pay = {
            'weekly': 52,
            'bi-weekly': 26,
            'monthly': 12,
            'bi-monthly': 6,
            'quarterly': 4,
            'semi-annually': 2,
            'annually': 1,
        }
        for contract in self.browse(cr, uid, ids, context):
            if contract.schedule_pay and schedule_pay.get(contract.schedule_pay, False):
                res[contract.id] = schedule_pay[contract.schedule_pay]

        return res

    # 'pays_per_year': fields.Function(
    #     _get_pays_per_year, method=True, string='Pays Per Year',
    #     type='float', readonly=True,
    # ),
    weeks_of_vacation = fields.Integer('Number of weeks of vacation', required=True)

    _defaults = {
        'weeks_of_vacation': 2,
    }
