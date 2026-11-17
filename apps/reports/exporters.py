from datetime import date, datetime, timezone, timedelta
from io import BytesIO

UTC3 = timezone(timedelta(hours=3))


class ExcelExporter:
    """Exports project data to a multi-sheet Excel file using openpyxl."""

    def export(self, project) -> bytes:
        from openpyxl import Workbook

        wb = Workbook()
        self._tasks_sheet(wb, project)
        self._kpis_sheet(wb, project)
        if wb.sheetnames and wb.sheetnames[0] == 'Sheet':
            del wb['Sheet']

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def _header_style(self, ws, headers):
        from openpyxl.styles import Font, PatternFill
        fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = fill

    def _tasks_sheet(self, wb, project):
        from openpyxl.styles import PatternFill, Font
        ws = wb.create_sheet('Tâches')
        headers = ['Code WBS', 'Nom', 'Statut', 'Début prévu', 'Fin prévue',
                   'Durée (j)', 'Avancement (%)', 'Critique']
        self._header_style(ws, headers)
        red_fill = PatternFill(start_color='FFEBEE', end_color='FFEBEE', fill_type='solid')
        red_font = Font(color='C0392B', bold=True)
        for i, task in enumerate(project.tasks.filter(is_summary=False).order_by('order'), 2):
            ws.cell(i, 1, task.wbs_code)
            ws.cell(i, 2, '  ' * task.level + task.name)
            ws.cell(i, 3, task.get_status_display())
            ws.cell(i, 4, str(task.planned_start))
            ws.cell(i, 5, str(task.planned_end))
            ws.cell(i, 6, float(task.planned_duration))
            ws.cell(i, 7, float(task.percent_complete))
            ws.cell(i, 8, 'Oui' if task.is_critical else 'Non')
            if task.is_critical:
                for col in range(1, 9):
                    ws.cell(i, col).fill = red_fill
                ws.cell(i, 8).font = red_font

    def _kpis_sheet(self, wb, project):
        ws = wb.create_sheet('KPIs')
        kpi = project.kpis.first()
        if not kpi:
            ws.cell(1, 1, 'Aucun KPI calculé')
            return
        health_labels = {'green': 'Dans les délais', 'orange': 'En retard', 'red': 'Dépassé'}
        rows = [
            ('Indicateur', 'Valeur'),
            ('Date de calcul', str(kpi.status_date)),
            ('Avancement global', f'{kpi.overall_percent_complete}%'),
            ('Tâches terminées', f'{kpi.completed_tasks}/{kpi.total_tasks}'),
            ('Tâches en retard', kpi.overdue_tasks),
            ('Tâches critiques', kpi.critical_tasks_count),
            ('Jalons atteints', f'{kpi.milestones_reached}/{kpi.milestones_total}'),
            ('Santé planning', health_labels.get(kpi.schedule_health, kpi.schedule_health)),
        ]
        if kpi.baseline_id:
            rows.insert(-1, ('SPI (indice planning)', float(kpi.spi)))
            rows.insert(-1, ('SV (écart planning)', float(kpi.sv)))
        for row_idx, (label, value) in enumerate(rows, 1):
            ws.cell(row_idx, 1, label)
            ws.cell(row_idx, 2, value)


class PDFExporter:
    """Exports project summary as PDF using reportlab."""

    def export(self, project) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm,
                                title=project.name,
                                author='StratEdge')
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('title', parent=styles['Title'], spaceAfter=20)
        story.append(Paragraph(f'Rapport de projet : {project.name}', title_style))
        now = datetime.now(UTC3).strftime('%d/%m/%Y à %Hh%M')
        story.append(Paragraph(f'Généré le {now} (UTC+3)', styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph('Informations générales', styles['Heading2']))
        info_data = [
            ['Statut', project.get_status_display()],
            ['Date début', str(project.start_date)],
            ['Date fin', str(project.end_date)],
            ['Avancement', f'{project.progress}%'],
        ]
        t = Table(info_data, colWidths=[5*cm, 10*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (1, 0), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        kpi = project.kpis.first()
        if kpi:
            story.append(Paragraph('Indicateurs de planning', styles['Heading2']))
            kpi_data = [
                ['Indicateur', 'Valeur', 'Statut'],
                ['SPI (indice planning)', f'{kpi.spi:.3f}', kpi.schedule_health],
                ['SV (écart planning)', f'{kpi.sv:.0f}', ''],
            ]
            kt = Table(kpi_data, colWidths=[7*cm, 4*cm, 4*cm])
            kt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(kt)
            story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph('Résumé des tâches', styles['Heading2']))
        tasks = project.tasks.filter(is_summary=False).order_by('order')[:30]
        task_data = [['Code WBS', 'Nom', 'Statut', 'Avancement', 'Critique']]
        for task in tasks:
            task_data.append([
                task.wbs_code or '',
                task.name[:40],
                task.get_status_display(),
                f'{task.percent_complete}%',
                'Oui' if task.is_critical else 'Non',
            ])
        tt = Table(task_data, colWidths=[2*cm, 7*cm, 3*cm, 2.5*cm, 2*cm])
        tt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
        ]))
        story.append(tt)

        doc.build(story)
        return buffer.getvalue()
