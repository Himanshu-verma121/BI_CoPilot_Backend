import io                     
import pandas as pd
from reportlab.lib.pagesizes  import letter, A4
from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units      import inch
from reportlab.lib            import colors
from reportlab.platypus       import (
    SimpleDocTemplate,   
    Table,              
    TableStyle,         
    Paragraph,           
    Spacer,              
    HRFlowable          
)
from datetime                 import datetime
import xlsxwriter            


def export_to_excel(
    question    : str,
    sql_query   : str,
    data        : list,
    company_name: str = "Company"
) -> bytes:
    
    output = io.BytesIO()

    workbook = xlsxwriter.Workbook(output)

    # Define Formats 
    header_format = workbook.add_format({
        "bold"      : True,
        "font_color": "#FFFFFF",
        "bg_color"  : "#667eea",
        "border"    : 1,
        "align"     : "center",
        "valign"    : "vcenter",
        "font_size" : 12
    })

    # Data rows 
    data_format = workbook.add_format({
        "border"   : 1,
        "font_size": 11,
        "valign"   : "vcenter"
    })

    # Title format
    title_format = workbook.add_format({
        "bold"     : True,
        "font_size": 16,
        "color"    : "#667eea"
    })

    # Results Sheet
    results_sheet = workbook.add_worksheet("Results")
    results_sheet.set_zoom(100)

    # Write title
    results_sheet.write(0, 0, f"Query Results — {company_name}", title_format)
    results_sheet.write(1, 0, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    results_sheet.write(2, 0, f"Question: {question}")

    if data:
        columns = list(data[0].keys())

        for col_idx, col_name in enumerate(columns):
            results_sheet.write(4, col_idx, col_name, header_format)
            results_sheet.set_column(col_idx, col_idx, max(len(col_name) + 4, 15))

        # Data rows
        for row_idx, row in enumerate(data):
            for col_idx, col_name in enumerate(columns):
                value = row.get(col_name, "")
                results_sheet.write(row_idx + 5, col_idx, value, data_format)

        # Autofilter 
        results_sheet.autofilter(4, 0, 4, len(columns) - 1)

        # Freeze top rows (title + headers stay visible when scrolling)
        results_sheet.freeze_panes(5, 0)

    # Query Info Sheet
    info_sheet = workbook.add_worksheet("Query Info")
    info_sheet.write(0, 0, "Question", header_format)
    info_sheet.write(1, 0, question)
    info_sheet.write(3, 0, "SQL Query Generated", header_format)
    info_sheet.write(4, 0, sql_query or "N/A")
    info_sheet.write(6, 0, "Export Time")
    info_sheet.write(7, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    info_sheet.set_column(0, 0, 80)    # wide column for SQL

    workbook.close()

    output.seek(0)    
    return output.read()


def export_to_pdf(
    question    : str,
    answer      : str,
    sql_query   : str,
    data        : list,
    company_name: str = "Company"
) -> bytes:
    output = io.BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(
        output,
        pagesize   = A4,
        rightMargin= 0.75 * inch,
        leftMargin = 0.75 * inch,
        topMargin  = 1 * inch,
        bottomMargin= 0.75 * inch
    )

    # Default styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent    = styles["Title"],
        fontSize  = 20,
        textColor = colors.HexColor("#667eea"),
        spaceAfter= 12
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent    = styles["Heading2"],
        fontSize  = 13,
        textColor = colors.HexColor("#1a1a2e"),
        spaceBefore= 16,
        spaceAfter = 8
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent    = styles["Normal"],
        fontSize  = 10,
        textColor = colors.HexColor("#333333"),
        spaceAfter= 8
    )

    # PDF Content
    story = []

    # Title
    story.append(Paragraph(f"BI Co-Pilot — Query Report", title_style))
    story.append(Paragraph(f"{company_name}", styles["Normal"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#667eea")))
    story.append(Spacer(1, 0.2 * inch))

    # Question section
    story.append(Paragraph("Question", heading_style))
    story.append(Paragraph(question, body_style))

    # Answer section
    if answer:
        story.append(Paragraph("AI Analysis", heading_style))
        story.append(Paragraph(answer, body_style))

    # SQL Query section
    if sql_query:
        story.append(Paragraph("SQL Query Generated", heading_style))
        sql_style = ParagraphStyle(
            "SQL",
            parent     = styles["Code"],
            fontSize   = 8,
            backColor  = colors.HexColor("#f5f5f5"),
            textColor  = colors.HexColor("#333333"),
            fontName   = "Courier",
            leftIndent = 12,
            spaceAfter = 12
        )
        story.append(Paragraph(sql_query.replace("\n", "<br/>"), sql_style))

    # Data table
    if data:
        story.append(Paragraph("Query Results", heading_style))
        story.append(Paragraph(f"Total rows: {len(data)}", body_style))

        columns = list(data[0].keys())

        table_data = [columns]    # header row

        # Data rows (max 100 rows in PDF)
        for row in data[:100]:
            table_row = [str(row.get(col, ""))[:50] for col in columns]
            table_data.append(table_row)

        if len(data) > 100:
            story.append(Paragraph(
                f"Note: Showing first 100 of {len(data)} rows. Download Excel for complete data.",
                body_style
            ))

        # Creating table
        col_widths  = [6.5 * inch / len(columns)] * len(columns)
        pdf_table   = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Style the table
        pdf_table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#667eea")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,0), 10),
            ("ALIGN",      (0,0), (-1,0), "CENTER"),

            # Data rows
            ("FONTSIZE",   (0,1), (-1,-1), 8),
            ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#f8f9ff")]),   

            # Grid
            ("GRID",     (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
            ("VALIGN",   (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))

        story.append(pdf_table)

    # PDF
    doc.build(story)

    output.seek(0)
    return output.read()