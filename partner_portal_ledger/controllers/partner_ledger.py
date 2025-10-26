import logging
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64
from odoo import http
from odoo.http import request
from odoo.tools import date_utils
from datetime import datetime
import csv
from io import StringIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

_logger = logging.getLogger(__name__)

class CustomerLedgerController(http.Controller):

    @http.route('/my/ledger', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def show_ledger(self, **kw):
        partner = request.env.user.partner_id
        user = request.env['res.users'].browse(request.env.uid)
        lang_code = user.lang or 'en_US'
        lang = request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang.date_format if lang else '%Y-%m-%d'
        _logger.info(f"User: {user.name}, Lang: {lang_code}, Date Format: {date_format}")

        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        search_term = kw.get('search_term', '')
        group_by = kw.get('group_by', 'none')
        _logger.info(f"Filter Inputs - date_from: {date_from}, date_to: {date_to}, search_term: {search_term}, group_by: {group_by}")

        domain = [
            ('partner_id', '=', partner.id),
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_payable'])
        ]

        if date_from:
            try:
                parsed_date = datetime.strptime(date_from, '%Y-%m-%d')
                date_from_formatted = parsed_date.strftime(date_format)
                domain.append(('date', '>=', date_from))
                _logger.info(f"Applied date_from filter: {date_from} (formatted: {date_from_formatted})")
            except ValueError as e:
                _logger.warning(f"Invalid date_from: {date_from}, Error: {str(e)}")
                date_from = None
        if date_to:
            try:
                parsed_date = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_formatted = parsed_date.strftime(date_format)
                domain.append(('date', '<=', date_to))
                _logger.info(f"Applied date_to filter: {date_to} (formatted: {date_to_formatted})")
            except ValueError as e:
                _logger.warning(f"Invalid date_to: {date_to}, Error: {str(e)}")
                date_to = None
        if search_term:
            domain += ['|', ('name', 'ilike', search_term), ('move_id.name', 'ilike', search_term)]
            _logger.info(f"Applied search_term filter: {search_term}")

        lines = request.env['account.move.line'].sudo().search(domain, order='date desc')
        _logger.info(f"Ledger entries fetched: {len(lines)} records")

        grouped_lines = {}
        if group_by != 'none':
            for line in lines:
                if group_by == 'day':
                    key = line.date.strftime(date_format)
                elif group_by == 'month':
                    key = line.date.strftime('%Y-%m')
                elif group_by == 'year':
                    key = line.date.strftime('%Y')
                if key not in grouped_lines:
                    grouped_lines[key] = []
                grouped_lines[key].append(line)
        else:
            grouped_lines = {'all': lines}

        table_content = ""
        for group_key, group_lines in sorted(grouped_lines.items(), reverse=True):
            if group_by != 'none':
                table_content += f"""
                    <tr class="group-header">
                        <th colspan="7">{group_key}</th>
                    </tr>
                """
            for line in group_lines:
                table_content += f"""
                    <tr class="table-row">
                        <td>{line.date.strftime(date_format)}</td>
                        <td>{line.move_id.name or ''}</td>
                        <td>{line.name or ''}</td>
                        <td class="text-end">{line.debit:.2f}</td>
                        <td class="text-end">{line.credit:.2f}</td>
                        <td class="text-end">{line.balance:.2f}</td>
                        <td class="text-center">
                            <button class="btn btn-sm btn-outline-primary view-btn" onclick="showDetails('{line.id}')">
                                👁
                            </button>
                        </td>
                    </tr>
                """

        csrf_token = request.csrf_token()
        _logger.info(f"CSRF Token: {csrf_token}")

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Ledger - {partner.name}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    background-color: #f5f6f5;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    font-size: 14px;
                    color: #2d3748;
                }}
                .container {{
                    max-width: 1200px;
                    margin-top: 2rem;
                }}
                h1 {{
                    font-size: 1.8rem;
                    font-weight: 600;
                    color: #2d3748;
                    text-align: center;
                    margin-bottom: 2rem;
                }}
                .card {{
                    border: none;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                    background-color: #ffffff;
                }}
                .form-label {{
                    font-size: 0.85rem;
                    color: #4a5568;
                }}
                .form-control, .form-select {{
                    font-size: 0.85rem;
                    border-radius: 6px;
                    border: 1px solid #e2e8f0;
                    transition: border-color 0.2s ease-in-out;
                }}
                .form-control:focus, .form-select:focus {{
                    border-color: #5a9bd5;
                    box-shadow: 0 0 0 3px rgba(90, 155, 213, 0.2);
                }}
                .table {{
                    border-radius: 8px;
                    overflow: hidden;
                    background-color: #ffffff;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }}
                .table th {{
                    background-color: #5a9bd5;
                    color: #ffffff;
                    font-size: 0.8rem;
                    text-transform: uppercase;
                    font-weight: 500;
                    padding: 12px;
                }}
                .table td {{
                    padding: 10px;
                    vertical-align: middle;
                    color: #2d3748;
                }}
                .group-header th {{
                    background-color: #edf2f7;
                    color: #2d3748;
                    font-weight: 500;
                    padding: 10px;
                }}
                .table-row {{
                    transition: background-color 0.3s ease;
                }}
                .table-row:hover {{
                    background-color: #f7fafc;
                }}
                .view-btn {{
                    font-size: 0.9rem;
                    padding: 4px 8px;
                    border-radius: 4px;
                    transition: background-color 0.2s ease, transform 0.2s ease;
                }}
                .view-btn:hover {{
                    background-color: #5a9bd5;
                    color: #ffffff;
                    transform: scale(1.05);
                }}
                .modal-content {{
                    border-radius: 8px;
                    border: none;
                    animation: slideIn 0.3s ease;
                }}
                @keyframes slideIn {{
                    from {{ transform: translateY(-20px); opacity: 0; }}
                    to {{ transform: translateY(0); opacity: 1; }}
                }}
                .modal-header, .modal-body {{
                    background-color: #ffffff;
                }}
                .modal-header {{
                    border-bottom: 1px solid #e2e8f0;
                }}
                .footer {{
                    margin-top: 1.5rem;
                    text-align: right;
                    color: #4a5568;
                    font-size: 0.85rem;
                }}
                .export-btn-group {{
                    margin-bottom: 1rem;
                }}
                .export-btn-group .btn {{
                    font-size: 0.85rem;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body class="container">
            <h1>Customer Ledger - {partner.name}</h1>
            
            <!-- Filters Form -->
            <form id="ledger-filter-form" method="POST" class="mb-4 card p-4">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <div class="row g-3">
                    <div class="col-md-3">
                        <label for="date_from" class="form-label">From Date</label>
                        <input type="date" id="date_from" name="date_from" class="form-control" value="{date_from or ''}">
                    </div>
                    <div class="col-md-3">
                        <label for="date_to" class="form-label">To Date</label>
                        <input type="date" id="date_to" name="date_to" class="form-control" value="{date_to or ''}">
                    </div>
                    <div class="col-md-3">
                        <label for="search_term" class="form-label">Search Term</label>
                        <input type="text" id="search_term" name="search_term" class="form-control" placeholder="Search description or move..." value="{search_term}">
                    </div>
                    <div class="col-md-3">
                        <label for="group_by" class="form-label">Group By</label>
                        <select id="group_by" name="group_by" class="form-select">
                            <option value="none" {'selected' if group_by == 'none' else ''}>None</option>
                            <option value="day" {'selected' if group_by == 'day' else ''}>Day</option>
                            <option value="month" {'selected' if group_by == 'month' else ''}>Month</option>
                            <option value="year" {'selected' if group_by == 'year' else ''}>Year</option>
                        </select>
                    </div>
                </div>
            </form>

            <!-- Export Button -->
            <div class="export-btn-group text-end">
                <div class="btn-group">
                    <button type="button" class="btn btn-outline-primary dropdown-toggle" data-bs-toggle="dropdown">
                        Export
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="/my/ledger/export/pdf?date_from={date_from or ''}&date_to={date_to or ''}&search_term={search_term}&group_by={group_by}">PDF</a></li>
                        <li><a class="dropdown-item" href="/my/ledger/export/xlsx?date_from={date_from or ''}&date_to={date_to or ''}&search_term={search_term}&group_by={group_by}">XLSX</a></li>
                        <li><a class="dropdown-item" href="/my/ledger/export/csv?date_from={date_from or ''}&date_to={date_to or ''}&search_term={search_term}&group_by={group_by}">CSV</a></li>
                    </ul>
                </div>
            </div>
            
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Move</th>
                            <th>Description</th>
                            <th class="text-end">Debit</th>
                            <th class="text-end">Credit</th>
                            <th class="text-end">Balance</th>
                            <th>View</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_content}
                    </tbody>
                </table>
            </div>

            <div class="footer">
                <p>Total Entries: {len(lines)}</p>
            </div>

            <!-- Modal -->
            <div class="modal fade" id="detailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Ledger Details</h5>
                            <button type="button" class="btn-close" onclick="closeModal()"></button>
                        </div>
                        <div class="modal-body" id="modal-body">
                            Loading...
                        </div>
                    </div>
                </div>
            </div>

            <script>
                function showDetails(line_id) {{
                    fetch('/my/ledger/detail/' + line_id, {{ headers: {{ 'X-CSRF-Token': '{csrf_token}' }} }})
                        .then(response => response.text())
                        .then(html => {{
                            document.getElementById('modal-body').innerHTML = html;
                            new bootstrap.Modal(document.getElementById('detailModal')).show();
                        }});
                }}
                function closeModal() {{
                    bootstrap.Modal.getInstance(document.getElementById('detailModal')).hide();
                }}

                let timeout;
                document.querySelectorAll('#ledger-filter-form input, #ledger-filter-form select').forEach(element => {{
                    element.addEventListener('change', () => {{
                        clearTimeout(timeout);
                        timeout = setTimeout(() => {{
                            console.log('Submitting form with values:', {{
                                date_from: document.getElementById('date_from').value,
                                date_to: document.getElementById('date_to').value,
                                search_term: document.getElementById('search_term').value,
                                group_by: document.getElementById('group_by').value
                            }});
                            document.getElementById('ledger-filter-form').submit();
                        }}, 300);
                    }});
                }});
            </script>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        return html

    @http.route('/my/ledger/export/csv', type='http', auth='user', website=True)
    def export_csv(self, **kw):
        partner = request.env.user.partner_id
        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        search_term = kw.get('search_term', '')
        group_by = kw.get('group_by', 'none')

        user = request.env['res.users'].browse(request.env.uid)
        lang_code = user.lang or 'en_US'
        lang = request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang.date_format if lang else '%Y-%m-%d'

        domain = [
            ('partner_id', '=', partner.id),
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_payable'])
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if search_term:
            domain += ['|', ('name', 'ilike', search_term), ('move_id.name', 'ilike', search_term)]

        lines = request.env['account.move.line'].sudo().search(domain, order='date desc')

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Move', 'Description', 'Debit', 'Credit', 'Balance'])

        grouped_lines = {}
        if group_by != 'none':
            for line in lines:
                if group_by == 'day':
                    key = line.date.strftime(date_format)
                elif group_by == 'month':
                    key = line.date.strftime('%Y-%m')
                elif group_by == 'year':
                    key = line.date.strftime('%Y')
                if key not in grouped_lines:
                    grouped_lines[key] = []
                grouped_lines[key].append(line)
        else:
            grouped_lines = {'all': lines}

        for group_key, group_lines in sorted(grouped_lines.items(), reverse=True):
            if group_by != 'none':
                writer.writerow([f'Group: {group_key}'])
            for line in group_lines:
                writer.writerow([
                    line.date.strftime(date_format),
                    line.move_id.name or '',
                    line.name or '',
                    f'{line.debit:.2f}',
                    f'{line.credit:.2f}',
                    f'{line.balance:.2f}'
                ])

        csv_content = output.getvalue()
        output.close()

        return request.make_response(
            csv_content,
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', 'attachment; filename="customer_ledger.csv"')
            ]
        )

    @http.route('/my/ledger/export/xlsx', type='http', auth='user', website=True)
    def export_xlsx(self, **kw):
        partner = request.env.user.partner_id
        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        search_term = kw.get('search_term', '')
        group_by = kw.get('group_by', 'none')

        user = request.env['res.users'].browse(request.env.uid)
        lang_code = user.lang or 'en_US'
        lang = request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang.date_format if lang else '%Y-%m-%d'

        domain = [
            ('partner_id', '=', partner.id),
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_payable'])
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if search_term:
            domain += ['|', ('name', 'ilike', search_term), ('move_id.name', 'ilike', search_term)]

        lines = request.env['account.move.line'].sudo().search(domain, order='date desc')

        wb = Workbook()
        ws = wb.active
        ws.title = "Customer Ledger"
        ws.append(['Date', 'Move', 'Description', 'Debit', 'Credit', 'Balance'])

        grouped_lines = {}
        if group_by != 'none':
            for line in lines:
                if group_by == 'day':
                    key = line.date.strftime(date_format)
                elif group_by == 'month':
                    key = line.date.strftime('%Y-%m')
                elif group_by == 'year':
                    key = line.date.strftime('%Y')
                if key not in grouped_lines:
                    grouped_lines[key] = []
                grouped_lines[key].append(line)
        else:
            grouped_lines = {'all': lines}

        for group_key, group_lines in sorted(grouped_lines.items(), reverse=True):
            if group_by != 'none':
                ws.append([f'Group: {group_key}'])
            for line in group_lines:  # Fix: Use group_lines instead of lines
                ws.append([
                    line.date.strftime(date_format),
                    line.move_id.name or '',
                    line.name or '',
                    line.debit,
                    line.credit,
                    line.balance
                ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="customer_ledger.xlsx"')
            ]
        )
   
    @http.route('/my/ledger/export/pdf', type='http', auth='user', website=True)
    def export_pdf(self, **kw):
        partner = request.env.user.partner_id
        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        search_term = kw.get('search_term', '')
        group_by = kw.get('group_by', 'none')

        # Get Odoo's date format
        user = request.env['res.users'].browse(request.env.uid)
        lang_code = user.lang or 'en_US'
        lang = request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang.date_format if lang else '%Y-%m-%d'

        # Build base domain
        base_domain = [
            ('partner_id', '=', partner.id),
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_payable'])
        ]

        if search_term:
            base_domain += ['|', ('name', 'ilike', search_term), ('move_id.name', 'ilike', search_term)]

        # Compute opening balance
        opening_balance = 0.0
        if date_from:
            opening_domain = base_domain + [('date', '<', date_from)]
            opening_lines = request.env['account.move.line'].sudo().search(opening_domain)
            opening_balance = sum((l.debit - l.credit) for l in opening_lines)

        # Build domain for lines
        domain = base_domain[:]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        lines = request.env['account.move.line'].sudo().search(domain, order='date asc, id asc')

        # Compute running balances
        running_balance = opening_balance
        line_to_running = {}
        for line in lines:
            running_balance += line.debit - line.credit
            line_to_running[line.id] = running_balance

        output = io.BytesIO()
        # Use landscape orientation
        doc = SimpleDocTemplate(
            output,
            pagesize=(letter[1], letter[0]),  # Swap dimensions for landscape
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        title_style.fontSize = 14
        title_style.leading = 16
        title_style.alignment = 1
        custom_style = styles['Normal']
        custom_style.fontSize = 10
        custom_style.leading = 12  # Line spacing

        elements = []

        # Add customer name as a title
        elements.append(Paragraph(f"Customer Ledger - {partner.name}", title_style))
        elements.append(Spacer(1, 12))  # Add some space between title and table

        data = [['Date', 'Move', 'Description', 'Debit', 'Credit', 'Balance']]

        # Add opening balance if applicable
        if date_from:
            data.append(['Opening Balance', '', '', '', '', f'{opening_balance:.2f}'])

        grouped_lines = {}
        if group_by != 'none':
            for line in lines:
                if group_by == 'day':
                    key = line.date.strftime('%Y-%m-%d')
                elif group_by == 'month':
                    key = line.date.strftime('%Y-%m')
                elif group_by == 'year':
                    key = line.date.strftime('%Y')
                if key not in grouped_lines:
                    grouped_lines[key] = []
                grouped_lines[key].append(line)
        else:
            grouped_lines = {'all': lines}

        for group_key, group_lines in sorted(grouped_lines.items()):
            display_key = group_key
            if group_by == 'day':
                display_key = datetime.strptime(group_key, '%Y-%m-%d').strftime(date_format)
            if group_by != 'none':
                data.append([f'Group: {display_key}', '', '', '', '', ''])
            for line in group_lines:
                data.append([
                    line.date.strftime(date_format),
                    line.move_id.name or '',
                    Paragraph(line.name or '', style=custom_style) if line.name else '',
                    f'{line.debit:.2f}',
                    f'{line.credit:.2f}',
                    f'{line_to_running[line.id]:.2f}'
                ])

        table = Table(data, colWidths=[1.2 * inch, 1.2 * inch, 2.5 * inch, 0.8 * inch, 0.8 * inch, 1 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5a9bd5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)

        doc.build(elements)
        output.seek(0)

        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="customer_ledger.pdf"')
            ]
        )
        
    @http.route('/my/ledger/detail/<int:line_id>', type='http', auth='user', website=True, csrf=True)
    def ledger_detail(self, line_id):
        """ Show account.move and move.line details inside modal """
        line = request.env['account.move.line'].sudo().browse(line_id)
        move = line.move_id

        # Get Odoo's date format from the user's language settings
        user = request.env['res.users'].browse(request.env.uid)
        lang_code = user.lang or 'en_US'
        lang = request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang.date_format if lang else '%Y-%m-%d'

        html = f"""
        <h4 class="mb-3">Move: {move.name}</h4>
        <p class="mb-1"><strong>Date:</strong> {move.date.strftime(date_format)}</p>
        <p class="mb-1"><strong>Journal:</strong> {move.journal_id.name}</p>
        <p class="mb-1"><strong>Reference:</strong> {move.ref or '—'}</p>
        <hr class="my-3">
        <h5 class="mb-3">Move Lines</h5>
        <div class="table-responsive">
            <table class="table table-sm table-bordered">
                <thead class="table-light">
                    <tr>
                        <th>Account</th>
                        <th>Label</th>
                        <th class="text-end">Debit</th>
                        <th class="text-end">Credit</th>
                    </tr>
                </thead>
                <tbody>
        """
        for l in move.line_ids:
            html += f"""
                <tr>
                    <td>{l.account_id.name}</td>
                    <td>{l.name or ''}</td>
                    <td class="text-end">{l.debit:.2f}</td>
                    <td class="text-end">{l.credit:.2f}</td>
                </tr>
            """
        html += "</tbody></table></div>"
        return html
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomerLedgerController(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'ledger_count' in counters:
            partner = request.env.user.partner_id
            domain = [
                ('partner_id', '=', partner.id),
                ('account_id.account_type', 'in', ['asset_receivable', 'asset_payable'])
            ]
            values['ledger_count'] = request.env['account.move.line'].sudo().search_count(domain)
        return values

    # Your existing routes (show_ledger, export_csv, export_xlsx, export_pdf, ledger_detail) go here
    # ... (keep your existing code)