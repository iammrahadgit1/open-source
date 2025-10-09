import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64

from odoo import http
from odoo.http import request


class CustomerLedgerController(http.Controller):

# from odoo import http
# from odoo.http import request

# class CustomerLedgerController(http.Controller):

    @http.route('/my/ledger', type='http', auth='user', website=True)
    def show_ledger(self):
        # Get the logged-in user's partner
        partner = request.env.user.partner_id

        # Fetch ledger entries
        lines = request.env['account.move.line'].sudo().search([
            ('partner_id', '=', partner.id),
            ('account_id.account_type', 'in', ['asset_receivable', 'asset_payable'])
        ], order='date desc')

        # Prepare table rows
        rows = ""
        for line in lines:
            rows += f"""
                <tr>
                    <td>{line.date.strftime('%Y-%m-%d')}</td>
                    <td>{line.move_id.name or ''}</td>
                    <td>{line.name or ''}</td>
                    <td style="text-align:right;">{line.debit:.2f}</td>
                    <td style="text-align:right;">{line.credit:.2f}</td>
                    <td style="text-align:right;">{line.balance:.2f}</td>
                    <td style="text-align:center;">
                        <button class="view-btn" onclick="showDetails('{line.id}')">
                            👁
                        </button>
                    </td>
                </tr>
            """

        # Inline HTML + JS + CSS
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ledger - {partner.name}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 40px;
                    background-color: #f9fafb;
                    color: #333;
                }}
                h1 {{
                    text-align: center;
                    color: #222;
                    margin-bottom: 30px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                    background-color: #fff;
                    border-radius: 10px;
                    overflow: hidden;
                }}
                th, td {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #f0f0f0;
                }}
                th {{
                    background-color: #2b6cb0;
                    color: #fff;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                tr:hover {{
                    background-color: #f5faff;
                }}
                .view-btn {{
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 18px;
                }}
                .footer {{
                    margin-top: 20px;
                    text-align: right;
                    color: #666;
                    font-size: 14px;
                }}
                /* Modal styling */
                .modal {{
                    display: none;
                    position: fixed;
                    z-index: 1000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    overflow: auto;
                    background-color: rgba(0,0,0,0.6);
                }}
                .modal-content {{
                    background-color: #fff;
                    margin: 10% auto;
                    padding: 20px;
                    border-radius: 10px;
                    width: 60%;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                }}
                .close {{
                    float: right;
                    font-size: 22px;
                    font-weight: bold;
                    color: #333;
                    cursor: pointer;
                }}
            </style>
        </head>
        <body>
            <h1>Customer Ledger - {partner.name}</h1>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Move</th>
                        <th>Description</th>
                        <th style="text-align:right;">Debit</th>
                        <th style="text-align:right;">Credit</th>
                        <th style="text-align:right;">Balance</th>
                        <th>View</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>

            <div class="footer">
                <p>Total Entries: {len(lines)}</p>
            </div>

            <!-- Modal -->
            <div id="detailModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeModal()">&times;</span>
                    <div id="modal-body">Loading...</div>
                </div>
            </div>

            <script>
                function showDetails(line_id) {{
                    fetch('/my/ledger/detail/' + line_id)
                        .then(response => response.text())
                        .then(html => {{
                            document.getElementById('modal-body').innerHTML = html;
                            document.getElementById('detailModal').style.display = 'block';
                        }});
                }}
                function closeModal() {{
                    document.getElementById('detailModal').style.display = 'none';
                }}
            </script>
        </body>
        </html>
        """
        return html


    @http.route('/my/ledger/detail/<int:line_id>', type='http', auth='user', website=True)
    def ledger_detail(self, line_id):
        """ Show account.move and move.line details inside modal """
        line = request.env['account.move.line'].sudo().browse(line_id)
        move = line.move_id

        html = f"""
        <h2>Move: {move.name}</h2>
        <p><strong>Date:</strong> {move.date}</p>
        <p><strong>Journal:</strong> {move.journal_id.name}</p>
        <p><strong>Reference:</strong> {move.ref or '—'}</p>
        <hr>
        <h3>Move Lines</h3>
        <table style="width:100%; border-collapse:collapse;">
            <thead>
                <tr style="background:#2b6cb0;color:white;">
                    <th style="padding:6px;">Account</th>
                    <th style="padding:6px;">Label</th>
                    <th style="padding:6px;text-align:right;">Debit</th>
                    <th style="padding:6px;text-align:right;">Credit</th>
                </tr>
            </thead>
            <tbody>
        """
        for l in move.line_ids:
            html += f"""
                <tr>
                    <td style="padding:6px;">{l.account_id.name}</td>
                    <td style="padding:6px;">{l.name or ''}</td>
                    <td style="padding:6px;text-align:right;">{l.debit:.2f}</td>
                    <td style="padding:6px;text-align:right;">{l.credit:.2f}</td>
                </tr>
            """
        html += "</tbody></table>"
        return html



# class ChartController(http.Controller):

#     @http.route('/chart/seaborn', type='http', auth='public')
#     def seaborn_chart(self):
#         # Example dataset
#         data = sns.load_dataset("penguins")
        
#         # Create the plot
#         plt.figure(figsize=(10, 6))
#         sns.scatterplot(data=data, x="bill_length_mm", y="bill_depth_mm", hue="species", style="species")
#         plt.title("Penguins Scatter Plot")

#         # Save the chart to a bytes buffer
#         buf = io.BytesIO()
#         plt.savefig(buf, format="png")
#         buf.seek(0)
#         plt.close()

#         # Encode the image in base64
#         image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

#         # Generate an HTML page to display the image
#         html = f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <title>Seaborn Chart</title>
#         </head>
#         <body>
#             <h1>Seaborn Chart Example</h1>
#             <img src="data:image/png;base64,{image_base64}" />
#         </body>
#         </html>
#         """
#         return html
       