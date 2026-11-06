Payroll > Configuration > Settings > Quebec Payroll:

- enter the Revenu Québec identification number and the remittance
  frequency (monthly for a new employer);
- choose the Health Services Fund sector and the rate basis: total payroll
  of the previous year (enter it, associated employers included) or, for
  the first two years of contributions, the payroll paid since January 1;
  with that basis, keep the payroll of the associated employers paid since
  January 1 up to date each remittance period;
- with the previous-year basis, enter the previous-year payroll of the
  company alone subject to the WSDRF contribution (RL-1 summary line 51):
  the payslips accrue the WSDRF contribution only above its threshold;
- enter the CNESST rate per $100 of the classification decision of the
  year (leave 0 without CNESST coverage);
- check *Not Subject to the Labour Standards Contribution* only for the
  exempt employers (federal jurisdiction, charities, etc.).

Installing the module adds the Quebec rules to the *Canada - Base*
structure of every company and, with the `ca_2023` chart, proposes the
accounts (employer contributions 512121, source deductions payable 221206).
The *Set Up Canadian Payroll* button does the same for a new company.

On each contract whose province of employment is Quebec, page *Canadian
Payroll*: the TP-1015.3 claim (basic personal amount, or lines 7 and 9 of
the form with the year of the form, line 7 being indexed on the pays of the
following years), the deductions of line 19, the amounts authorized on a
TP-1016, with the date they apply from when it falls after the first pay of
the year, the Fonds de solidarité FTQ and Fondaction withholdings per pay,
the additional Quebec tax per pay, the exemption from withholding and the
CNESST coverage.

Employee contributions that reduce the Quebec taxable income (RPP, RRSP,
VRSP or PRPP, FHSA; variable F of TP-1015.F) go in salary rules of category
*Deduction Reducing the Quebec Taxable Income*, with a sequence below 110.

Due dates skip the Quebec public holidays and the Revenu Québec closure
days when the *Canada - Tax Compliance Calendar* module is installed;
otherwise only Saturdays and Sundays move them.

Payroll > Configuration > Canadian Time Parameters: add a version when
Revenu Québec publishes the rates of a new year (TP-1015.F, usually in
December).
