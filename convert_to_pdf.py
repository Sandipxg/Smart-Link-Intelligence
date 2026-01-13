"""
Convert Markdown documentation to PDF
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
import markdown
import re

def markdown_to_pdf(md_file, pdf_file):
    """Convert markdown file to PDF"""
    
    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_file, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=5
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#7f8c8d'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    code_style = ParagraphStyle(
        'Code',
        parent=styles['Code'],
        fontSize=9,
        leftIndent=20,
        rightIndent=20,
        spaceAfter=10,
        spaceBefore=10,
        fontName='Courier',
        backColor=colors.HexColor('#f4f4f4'),
        borderWidth=1,
        borderColor=colors.HexColor('#ddd'),
        borderPadding=10
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    # Split content into sections
    lines = md_content.split('\n')
    
    in_code_block = False
    code_block = []
    in_table = False
    table_data = []
    
    for line in lines:
        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block
                if code_block:
                    code_text = '\n'.join(code_block)
                    # Wrap long lines
                    wrapped_lines = []
                    for code_line in code_block:
                        if len(code_line) > 80:
                            # Simple wrapping
                            while len(code_line) > 80:
                                wrapped_lines.append(code_line[:80])
                                code_line = '  ' + code_line[80:]
                            wrapped_lines.append(code_line)
                        else:
                            wrapped_lines.append(code_line)
                    code_text = '\n'.join(wrapped_lines)
                    elements.append(Preformatted(code_text, code_style))
                    elements.append(Spacer(1, 0.2*inch))
                code_block = []
                in_code_block = False
            else:
                # Start of code block
                in_code_block = True
            continue
        
        if in_code_block:
            code_block.append(line)
            continue
        
        # Handle tables
        if line.strip().startswith('|') and '|' in line:
            if not in_table:
                in_table = True
                table_data = []
            
            # Parse table row
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            # Skip separator rows
            if all(set(cell.replace('-', '').strip()) == set() for cell in cells):
                continue
            
            table_data.append(cells)
            continue
        else:
            if in_table:
                # End of table - create table
                if table_data:
                    t = Table(table_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ]))
                    elements.append(t)
                    elements.append(Spacer(1, 0.2*inch))
                table_data = []
                in_table = False
        
        # Handle headings
        if line.startswith('# '):
            text = line[2:].strip()
            if 'Smart Link Intelligence' in text and len(elements) == 0:
                elements.append(Paragraph(text, title_style))
            else:
                elements.append(Paragraph(text, h1_style))
            elements.append(Spacer(1, 0.1*inch))
        elif line.startswith('## '):
            elements.append(Paragraph(line[3:].strip(), h2_style))
            elements.append(Spacer(1, 0.1*inch))
        elif line.startswith('### '):
            elements.append(Paragraph(line[4:].strip(), h3_style))
            elements.append(Spacer(1, 0.05*inch))
        elif line.startswith('#### '):
            elements.append(Paragraph(f"<b>{line[5:].strip()}</b>", body_style))
        elif line.startswith('---'):
            elements.append(Spacer(1, 0.2*inch))
        elif line.strip() == '':
            elements.append(Spacer(1, 0.1*inch))
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            # Bullet point
            text = line.strip()[2:]
            elements.append(Paragraph(f"• {text}", body_style))
        elif re.match(r'^\d+\.', line.strip()):
            # Numbered list
            text = re.sub(r'^\d+\.\s*', '', line.strip())
            elements.append(Paragraph(f"{line.strip()[:3]} {text}", body_style))
        else:
            # Regular paragraph
            if line.strip():
                # Handle inline code
                line = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#e74c3c">\1</font>', line)
                # Handle bold
                line = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', line)
                # Handle italic
                line = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', line)
                elements.append(Paragraph(line, body_style))
    
    # Build PDF
    doc.build(elements)
    print(f"PDF created successfully: {pdf_file}")

if __name__ == "__main__":
    markdown_to_pdf("DEVELOPER_DOCUMENTATION.md", "DEVELOPER_DOCUMENTATION.pdf")
