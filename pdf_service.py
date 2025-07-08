from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import os
from datetime import datetime
from flask import current_app

class PDFReportService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Définir des styles personnalisés pour le PDF"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e')
        ))
        
        self.styles.add(ParagraphStyle(
            name='ResultText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leftIndent=20
        ))
    
    def generate_analysis_report(self, analyse_result):
        """Générer un rapport PDF pour une analyse"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # En-tête
        story.append(Paragraph("MEDISCAN", self.styles['CustomTitle']))
        story.append(Paragraph("Rapport d'Analyse Médicale", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Informations patient
        story.append(Paragraph("INFORMATIONS PATIENT", self.styles['CustomHeading']))
        
        patient_data = [
            ['Nom:', f"{analyse_result.patient.nom} {analyse_result.patient.prenom}"],
            ['Date de naissance:', analyse_result.patient.date_naissance.strftime('%d/%m/%Y') if analyse_result.patient.date_naissance else 'Non renseignée'],
            ['Sexe:', analyse_result.patient.sexe or 'Non renseigné'],
            ['Médecin traitant:', analyse_result.patient.medecin_traitant or 'Non renseigné']
        ]
        
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(patient_table)
        story.append(Spacer(1, 20))
        
        # Informations analyse
        story.append(Paragraph("INFORMATIONS ANALYSE", self.styles['CustomHeading']))
        
        analyse_data = [
            ['Date d\'analyse:', analyse_result.date_analyse.strftime('%d/%m/%Y à %H:%M')],
            ['Médecin:', analyse_result.medecin.username],
            ['Statut:', 'POSITIF' if analyse_result.test_positif else 'NÉGATIF'],
        ]
        
        if analyse_result.type_anomalie:
            analyse_data.append(['Anomalies détectées:', analyse_result.type_anomalie.replace(',', ', ')])
        
        analyse_table = Table(analyse_data, colWidths=[2*inch, 4*inch])
        analyse_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(analyse_table)
        story.append(Spacer(1, 20))
        
        # Image d'analyse si disponible
        if analyse_result.image_path:
            story.append(Paragraph("IMAGE D'ANALYSE", self.styles['CustomHeading']))
            try:
                image_path = os.path.join(current_app.root_path, 'static', analyse_result.image_path)
                if os.path.exists(image_path):
                    img = Image(image_path, width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 20))
            except Exception as e:
                story.append(Paragraph("Image non disponible", self.styles['ResultText']))
                story.append(Spacer(1, 20))
        
        # Résultats et recommandations
        story.append(Paragraph("RÉSULTATS ET RECOMMANDATIONS", self.styles['CustomHeading']))
        
        if analyse_result.recommandation:
            story.append(Paragraph("Recommandations automatiques:", self.styles['Normal']))
            story.append(Paragraph(analyse_result.recommandation, self.styles['ResultText']))
            story.append(Spacer(1, 10))
        
        if analyse_result.commentaire_medecin:
            story.append(Paragraph("Commentaire du médecin:", self.styles['Normal']))
            story.append(Paragraph(analyse_result.commentaire_medecin, self.styles['ResultText']))
            story.append(Spacer(1, 20))
        
        # Pied de page
        story.append(Spacer(1, 30))
        story.append(Paragraph("_" * 50, self.styles['Normal']))
        story.append(Paragraph(f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", 
                              self.styles['Normal']))
        story.append(Paragraph("Ce rapport a été généré automatiquement par MediScan", 
                              self.styles['Normal']))
        
        # Construire le PDF
        doc.build(story)
        
        # Retourner le buffer
        buffer.seek(0)
        return buffer
    
    def generate_patient_history_report(self, patient):
        """Générer un rapport historique pour un patient"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # En-tête
        story.append(Paragraph("MEDISCAN", self.styles['CustomTitle']))
        story.append(Paragraph("Historique Patient", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Informations patient
        story.append(Paragraph("INFORMATIONS PATIENT", self.styles['CustomHeading']))
        story.append(Paragraph(f"Nom: {patient.nom} {patient.prenom}", self.styles['ResultText']))
        if patient.date_naissance:
            story.append(Paragraph(f"Date de naissance: {patient.date_naissance.strftime('%d/%m/%Y')}", 
                                 self.styles['ResultText']))
        story.append(Spacer(1, 20))
        
        # Historique des analyses
        story.append(Paragraph("HISTORIQUE DES ANALYSES", self.styles['CustomHeading']))
        
        analyses = patient.analyses.order_by('date_analyse').all()
        
        if analyses:
            # Créer un tableau avec l'historique
            data = [['Date', 'Résultat', 'Anomalies', 'Médecin']]
            
            for analyse in analyses:
                data.append([
                    analyse.date_analyse.strftime('%d/%m/%Y'),
                    'POSITIF' if analyse.test_positif else 'NÉGATIF',
                    analyse.type_anomalie or 'Aucune',
                    analyse.medecin.username
                ])
            
            table = Table(data, colWidths=[1.5*inch, 1*inch, 2*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("Aucune analyse trouvée pour ce patient.", self.styles['ResultText']))
        
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", 
                              self.styles['Normal']))
        
        # Construire le PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer

# Instance globale
pdf_service = PDFReportService()
