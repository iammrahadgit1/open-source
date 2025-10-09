{
    "name": "Custom Accounts",
    "description": "reports",
    "summary": "Data seen",
    "author": "Ahad AmazeWorks Technologies",
    "version": "18.0.0.1",
    "depends": [ "account",'web'],
    "data": [
        # 'controllers/partner_ledger.xml',
        # 'controllers/sale.xml',
        # 'reports/sale_order.xml',
        # 'reports/purchase_order.xml',
        # 'reports/account_move.xml',
    ],
    'external_dependencies': {
        'python': [
            'seaborn',
        ],
    },
    "installable": True,
    "application": False,
}
