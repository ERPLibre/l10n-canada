# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2010 - 2014 Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Supplier on expense line",
    "version": "7.0.1.2.0",
    "author": "Savoir-faire Linux,Odoo Community Association (OCA)",
    "website": "http://www.savoirfairelinux.com",
    "category": "Human Resources",
    "license": "AGPL-3",
    "description": """
Supplier on expense line
========================
This module adds a supplier field on the expense line.

A second module will automatically install after this one, setting the field
as 'required'. We need to separate this in 2 modules because we need the demo
expense lines to have a supplier before setting the field required. This is
done in order to avoid warnings on installation with demo data activated.

Contributors
------------
* Jonatan Cloutier <jonatan.cloutier@savoirfairelinux.com>
* Maxime Chambreuil <maxime.chambreuil@savoirfairelinux.com>
* Sandy Carter <sandy.carter@savoirfairelinux.com>
* Agathe Mollé <agathe.molle@savoirfairelinux.com>
""",
    "depends": ['hr_expense'],
    "data": [
        'hr_expense_line_view.xml',
    ],
    "demo": [
        'hr_expense_line_demo.xml'
    ],
    "installable": True
}
