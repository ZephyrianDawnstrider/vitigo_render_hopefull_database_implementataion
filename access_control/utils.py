from .permissions import PermissionManager
import csv
from io import StringIO, BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

def get_template_path(base_template, user_role):
    """
    Resolves template path based on user role using the permission system.
    """
    permissions = PermissionManager.get_permissions(user_role)
    module_name = base_template.split('/')[0]  # Extract module name from template
    
    if module_name in permissions and permissions[module_name]['can_access']:
        base_path = permissions[module_name]['template_path']
        return base_path.format(role=user_role.lower()) + base_template
    
    return None

def generate_csv(roles, modules):
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Role Name', 'Display Name', 'Template Folder', 'Total Users', 'Module Permissions'])
    
    # Write data
    for role in roles:
        permissions = []
        for module in modules:
            try:
                perm = role.modulepermission_set.get(module=module)
                perm_str = f"{module.display_name}: "
                perm_str += "Access, " if perm.can_access else ""
                perm_str += "Modify, " if perm.can_modify else ""
                perm_str += "Delete" if perm.can_delete else ""
                permissions.append(perm_str.strip(', '))
            except:
                continue
                
        writer.writerow([
            role.name,
            role.display_name,
            role.template_folder,
            role.users.count(),
            ' | '.join(permissions)
        ])
    
    return output.getvalue()

def generate_pdf(roles, modules):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph('Access Control Report', title_style))
    elements.append(Spacer(1, 20))

    # Generate data for table
    data = [['Role', 'Display Name', 'Users', 'Permissions']]
    
    for role in roles:
        permissions = []
        for module in modules:
            try:
                perm = role.modulepermission_set.get(module=module)
                perm_str = f"{module.display_name}: "
                perms = []
                if perm.can_access: perms.append("Access")
                if perm.can_modify: perms.append("Modify")
                if perm.can_delete: perms.append("Delete")
                perm_str += ", ".join(perms)
                permissions.append(perm_str)
            except:
                continue

        data.append([
            role.name,
            role.display_name,
            str(role.users.count()),
            "\n".join(permissions)
        ])

    # Create table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return buffer.getvalue()