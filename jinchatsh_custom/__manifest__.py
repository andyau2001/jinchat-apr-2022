# -*- coding: utf-8 -*-
{
	'name': 'Jinchatsh Customize',
	'author': 'Youaddon',
	'version': '15.0.0.0',
	'live_test_url': ' ',
	'summary': 'Jinchatsh Customize',
	'description': """Jinchatsh Customize""",
	'license': "OPL-1",
	'depends': ['account', 'base', 'sale'],
	'data': [

	],
	'assets': {
		'web.assets_backend': [
			'jinchatsh_custom/static/src/js/attachment_viewer.js',
			'jinchatsh_custom/static/src/widgets/*/*.js',
		],
	},
	'installable': True,
	'auto_install': False,
	'category': 'Customizations',
}
