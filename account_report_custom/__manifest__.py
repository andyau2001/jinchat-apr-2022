# -*- coding: utf-8 -*-
{
	'name': 'Account Customize Report',
	'author': 'Youaddon',
	'version': '15.0.0.0',
	'live_test_url': ' ',
	'summary': 'Account Customize Report',
	'description': """Account Customize Report""",
	'license': "OPL-1",
	'depends': ['account', 'account_reports', 'sale'],
	'data': [
		'security/ir.model.access.csv',
		'views/report_financial.xml',
	],
	'installable': True,
	'auto_install': False,
	'category': 'Customizations',
}
