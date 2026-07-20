import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def build_evidence_pdf(
    zone: str, 
    plant_id: str, 
    triggered_at_str: str, 
    active_rules: list, 
    gas_readings: list, 
    permits: list, 
    narration_data: dict
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#E11D48')
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # Header block
    story.append(Paragraph("SENTINELGRID INDUSTRIAL SAFETY REPORT", subtitle_style))
    story.append(Paragraph("Tier-3 Regulatory Evidence Packet", title_style))
    story.append(Spacer(1, 6))
    
    meta_text = f"<b>Facility/Plant:</b> {plant_id} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Emergency Zone:</b> {zone} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Report Generated:</b> {triggered_at_str}"
    story.append(Paragraph(meta_text, body_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#E2E8F0'), spaceBefore=4, spaceAfter=12))
    
    # Section 1: Executive AI Safety Narration
    explanation = narration_data.get("explanation", "No explanation available.")
    story.append(Paragraph("1. Executive Briefing & Incident Summary", heading_style))
    story.append(Paragraph(explanation, body_style))
    story.append(Spacer(1, 10))
    
    # Section 2: Applicable Regulatory Clause & Compliance Evidence
    ev_packet = narration_data.get("evidence_packet") or {}
    app_clause = ev_packet.get("applicable_clause", "N/A")
    clause_rel = ev_packet.get("clause_relation", "N/A")
    ev_summary = ev_packet.get("summary", "N/A")
    
    story.append(Paragraph("2. Regulatory Compliance Mapping", heading_style))
    clause_table_data = [
        [Paragraph("<b>Applicable Clause</b>", bold_body), Paragraph(app_clause, body_style)],
        [Paragraph("<b>Violation Context</b>", bold_body), Paragraph(clause_rel, body_style)],
        [Paragraph("<b>Rule Summary</b>", bold_body), Paragraph(ev_summary, body_style)]
    ]
    clause_table = Table(clause_table_data, colWidths=[130, 410])
    clause_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(clause_table)
    story.append(Spacer(1, 12))
    
    # Section 3: Triggered Safety Violations
    story.append(Paragraph("3. Triggered Safety Violations", heading_style))
    rules_table_data = [[
        Paragraph("<b>Rule Name</b>", bold_body),
        Paragraph("<b>Severity</b>", bold_body),
        Paragraph("<b>Reason / Contributing Factors</b>", bold_body)
    ]]
    for r in active_rules:
        r_name = r.get("rule_name", "UNKNOWN_RULE")
        sev = f"Tier {r.get('severity', 3)}"
        reason_text = r.get("reason", "N/A")
        rules_table_data.append([
            Paragraph(r_name, body_style),
            Paragraph(f"<font color='#E11D48'><b>{sev}</b></font>", body_style),
            Paragraph(reason_text, body_style)
        ])
    if len(rules_table_data) == 1:
        rules_table_data.append([Paragraph("No active rule violations recorded.", body_style), Paragraph("-", body_style), Paragraph("-", body_style)])
        
    rules_table = Table(rules_table_data, colWidths=[180, 70, 290])
    rules_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(rules_table)
    story.append(Spacer(1, 12))
    
    # Section 4: Contributing Telemetry & Active Permits
    story.append(Paragraph("4. Gas Sensor Readings & Active Work Permits", heading_style))
    
    # Sub-table: Gas readings
    gas_rows = [[Paragraph("<b>Gas Type</b>", bold_body), Paragraph("<b>Reading (PPM)</b>", bold_body), Paragraph("<b>Sensor Status</b>", bold_body), Paragraph("<b>Timestamp</b>", bold_body)]]
    for g in (gas_readings[:6] if gas_readings else []):
        gas_rows.append([
            Paragraph(str(g.get("gas_type", "N/A")), body_style),
            Paragraph(f"<b>{g.get('reading_ppm', 'N/A')}</b>", body_style),
            Paragraph(str(g.get("sensor_status", "normal")), body_style),
            Paragraph(str(g.get("timestamp", ""))[:19], body_style)
        ])
    if len(gas_rows) == 1:
        gas_rows.append([Paragraph("No gas readings logged in window.", body_style), Paragraph("-", body_style), Paragraph("-", body_style), Paragraph("-", body_style)])
        
    gas_table = Table(gas_rows, colWidths=[110, 110, 140, 180])
    gas_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(gas_table)
    story.append(Spacer(1, 8))
    
    # Sub-table: Permits
    permit_rows = [[Paragraph("<b>Permit ID</b>", bold_body), Paragraph("<b>Type</b>", bold_body), Paragraph("<b>Issued By</b>", bold_body), Paragraph("<b>Issued At</b>", bold_body)]]
    for p in (permits[:6] if permits else []):
        permit_rows.append([
            Paragraph(str(p.get("permit_id", "N/A")), body_style),
            Paragraph(str(p.get("permit_type", "N/A")), body_style),
            Paragraph(str(p.get("issued_by", "N/A")), body_style),
            Paragraph(str(p.get("issued_at", ""))[:19], body_style)
        ])
    if len(permit_rows) == 1:
        permit_rows.append([Paragraph("No active permits in zone.", body_style), Paragraph("-", body_style), Paragraph("-", body_style), Paragraph("-", body_style)])
        
    permit_table = Table(permit_rows, colWidths=[130, 130, 120, 160])
    permit_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(permit_table)
    story.append(Spacer(1, 16))
    
    # Footer
    footer_text = "Generated automatically by SentinelGrid AI Compound Safety Risk Engine. Certified for regulatory compliance and OSHA/OISD audit logging."
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=body_style, fontSize=8, textColor=colors.HexColor('#94A3B8'), alignment=1)))
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
