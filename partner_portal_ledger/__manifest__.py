{
    "name": "Partner Ledger Report",
    "description": "reports",
    "summary": "Data seen",
    "author": "Ahad AmazeWorks Technologies",
    "version": "1.0",
    "depends": [ "account",'web'],
    "data": [
        'security/ir.model.access.csv',
        'views/ledger.xml',
        'views/portal_ledger_template.xml'

    ],
    'external_dependencies': {
        'python': [
            'seaborn',
        ],
    },
    "installable": True,
    "application": False,
}
