import csv
import json
import io
from datetime import datetime, date
from flask import current_app, Response
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import xml.etree.ElementTree as ET
from xml.dom import minidom

class ExportService:
    """Service pour l'exportation de données en différents formats"""

    @staticmethod
    def export_analyses_csv(analyses):
        """Exporter les analyses en format CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        headers = [
            'ID Analyse', 'Date', 'Patient Nom', 'Patient Prénom', 'Patient Date Naissance',
            'Médecin Nom', 'Médecin Prénom', 'Anomalies Détectées', 'Résultat Global',
            'Commentaire Médecin', 'Recommendations', 'Score Confiance', 'Image Originale',
            'Image Résultat', 'Date Création', 'Date Modification'
        ]
        writer.writerow(headers)
        
        # Données
        for analyse in analyses:
            row = [
                analyse.id,
                analyse.date_analyse.strftime('%Y-%m-%d') if analyse.date_analyse else '',
                analyse.patient.nom if analyse.patient else '',
                analyse.patient.prenom if analyse.patient else '',
                analyse.patient.date_naissance.strftime('%Y-%m-%d') if analyse.patient and analyse.patient.date_naissance else '',
                analyse.medecin.nom if analyse.medecin else '',
                analyse.medecin.prenom if analyse.medecin else '',
                analyse.anomalies_detectees or '',
                analyse.resultat_global or '',
                analyse.commentaire_medecin or '',
                analyse.recommendations or '',
                analyse.confiance_score or '',
                analyse.image_originale or '',
                analyse.image_resultat or '',
                analyse.date_creation.strftime('%Y-%m-%d %H:%M:%S') if analyse.date_creation else '',
                analyse.date_modification.strftime('%Y-%m-%d %H:%M:%S') if analyse.date_modification else ''
            ]
            writer.writerow(row)
        
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_patients_csv(patients):
        """Exporter les patients en format CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        headers = [
            'ID Patient', 'Nom', 'Prénom', 'Date Naissance', 'Sexe', 'Numéro Sécurité Sociale',
            'Email', 'Téléphone', 'Adresse', 'Médecin Traitant', 'Groupe Sanguin',
            'Allergies', 'Antécédents Médicaux', 'Date Inscription', 'Nombre Analyses'
        ]
        writer.writerow(headers)
        
        # Données
        for patient in patients:
            row = [
                patient.id,
                patient.nom,
                patient.prenom,
                patient.date_naissance.strftime('%Y-%m-%d') if patient.date_naissance else '',
                patient.sexe or '',
                patient.numero_securite_sociale or '',
                patient.email or '',
                patient.telephone or '',
                patient.adresse or '',
                patient.medecin_traitant or '',
                patient.groupe_sanguin or '',
                patient.allergies or '',
                patient.antecedents_medicaux or '',
                patient.date_creation.strftime('%Y-%m-%d %H:%M:%S') if patient.date_creation else '',
                len(patient.analyses) if patient.analyses else 0
            ]
            writer.writerow(row)
        
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_audit_csv(audit_logs):
        """Exporter les logs d'audit en format CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        headers = [
            'ID', 'Timestamp', 'Utilisateur ID', 'Utilisateur Nom', 'Utilisateur Email',
            'Action', 'Détails', 'IP Address', 'User Agent', 'Succès', 'Métadonnées'
        ]
        writer.writerow(headers)
        
        # Données
        for log in audit_logs:
            row = [
                log.id,
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user_id,
                f"{log.user.nom} {log.user.prenom}" if log.user else '',
                log.user.email if log.user else '',
                log.action,
                log.details or '',
                log.ip_address or '',
                log.user_agent or '',
                'Oui' if log.success else 'Non',
                json.dumps(log.metadata) if log.metadata else ''
            ]
            writer.writerow(row)
        
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_statistics_csv(stats_data):
        """Exporter les statistiques en format CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Section des métriques principales
        writer.writerow(['MÉTRIQUES PRINCIPALES'])
        writer.writerow(['Métrique', 'Valeur'])
        writer.writerow(['Total Patients', stats_data.get('total_patients', 0)])
        writer.writerow(['Total Analyses', stats_data.get('total_analyses', 0)])
        writer.writerow(['Total Anomalies', stats_data.get('total_anomalies', 0)])
        writer.writerow(['Taux Précision', f"{stats_data.get('precision_rate', 0):.1f}%"])
        writer.writerow([])
        
        # Section des analyses par jour
        if 'daily_analyses_data' in stats_data:
            writer.writerow(['ANALYSES PAR JOUR'])
            writer.writerow(['Date', 'Nombre Analyses', 'Anomalies Détectées'])
            for day_data in stats_data['daily_analyses_data']:
                writer.writerow([
                    day_data['date'],
                    day_data['analyses'],
                    day_data['anomalies']
                ])
            writer.writerow([])
        
        # Section des types d'anomalies
        if 'anomaly_types_data' in stats_data:
            writer.writerow(['TYPES D\'ANOMALIES'])
            writer.writerow(['Type', 'Nombre'])
            for anomaly_type, count in stats_data['anomaly_types_data'].items():
                writer.writerow([anomaly_type, count])
        
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_fhir(analysis_data):
        """Exporter une analyse au format FHIR (JSON)"""
        
        # Structure FHIR pour un DiagnosticReport
        fhir_data = {
            "resourceType": "DiagnosticReport",
            "id": f"analysis-{analysis_data.id}",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                            "code": "LAB",
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "33743-4",
                        "display": "Blood cell morphology"
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{analysis_data.patient.id}",
                "display": f"{analysis_data.patient.prenom} {analysis_data.patient.nom}"
            },
            "effectiveDateTime": analysis_data.date_creation.isoformat() if analysis_data.date_creation else None,
            "issued": analysis_data.date_creation.isoformat() if analysis_data.date_creation else None,
            "performer": [
                {
                    "reference": f"Practitioner/{analysis_data.medecin.id}",
                    "display": f"Dr. {analysis_data.medecin.prenom} {analysis_data.medecin.nom}"
                }
            ],
            "conclusion": analysis_data.resultat_global or "",
            "conclusionCode": []
        }
        
        # Ajouter les anomalies détectées
        if analysis_data.anomalies_detectees:
            anomalies = analysis_data.anomalies_detectees.split(',')
            for anomalie in anomalies:
                anomalie = anomalie.strip()
                fhir_data["conclusionCode"].append({
                    "coding": [
                        {
                            "system": "http://diseasedetect.local/anomalies",
                            "code": anomalie.upper().replace(' ', '_'),
                            "display": anomalie
                        }
                    ]
                })
        
        # Ajouter les observations
        if analysis_data.commentaire_medecin:
            fhir_data["conclusion"] += f"\n\nCommentaire médical: {analysis_data.commentaire_medecin}"
        
        return json.dumps(fhir_data, indent=2, ensure_ascii=False)

    @staticmethod
    def export_to_hl7_v2(analysis_data):
        """Exporter une analyse au format HL7 v2"""
        
        # En-tête MSH (Message Header)
        msh = "MSH|^~\&|DiseaseDetect|Hospital|LIS|Lab|"
        msh += datetime.now().strftime("%Y%m%d%H%M%S")
        msh += "||ORU^R01^ORU_R01|1|P|2.5.1|||NE|NE|FR\r"
        
        # Segment PID (Patient Identification)
        pid = f"PID|1||{analysis_data.patient.id}^^^DiseaseDetect||"
        pid += f"{analysis_data.patient.nom}^{analysis_data.patient.prenom}||"
        if analysis_data.patient.date_naissance:
            pid += analysis_data.patient.date_naissance.strftime("%Y%m%d")
        pid += f"|{analysis_data.patient.sexe or ''}|||"
        if analysis_data.patient.adresse:
            pid += analysis_data.patient.adresse.replace('\n', ' ')
        pid += "||"
        if analysis_data.patient.telephone:
            pid += analysis_data.patient.telephone
        pid += "|\r"
        
        # Segment OBR (Observation Request)
        obr = f"OBR|1|{analysis_data.id}|{analysis_data.id}|33743-4^Blood cell morphology^LN|"
        obr += "|"
        if analysis_data.date_creation:
            obr += analysis_data.date_creation.strftime("%Y%m%d%H%M%S")
        obr += "|"
        if analysis_data.date_creation:
            obr += analysis_data.date_creation.strftime("%Y%m%d%H%M%S")
        obr += "||||||||"
        obr += f"{analysis_data.medecin.nom}^{analysis_data.medecin.prenom}^Dr|\r"
        
        # Segments OBX (Observation Results)
        obx_segments = ""
        obx_count = 1
        
        if analysis_data.anomalies_detectees:
            obx = f"OBX|{obx_count}|ST|ANOMALY^Anomalies détectées^L||"
            obx += analysis_data.anomalies_detectees
            obx += "||||||F\r"
            obx_segments += obx
            obx_count += 1
        
        if analysis_data.resultat_global:
            obx = f"OBX|{obx_count}|ST|RESULT^Résultat global^L||"
            obx += analysis_data.resultat_global
            obx += "||||||F\r"
            obx_segments += obx
            obx_count += 1
        
        if analysis_data.commentaire_medecin:
            obx = f"OBX|{obx_count}|ST|COMMENT^Commentaire médical^L||"
            obx += analysis_data.commentaire_medecin
            obx += "||||||F\r"
            obx_segments += obx
            obx_count += 1
        
        if analysis_data.confiance_score:
            obx = f"OBX|{obx_count}|NM|CONFIDENCE^Score de confiance^L||"
            obx += str(analysis_data.confiance_score)
            obx += "|%|||||F\r"
            obx_segments += obx
        
        return msh + pid + obr + obx_segments

    @staticmethod
    def create_csv_response(csv_data, filename):
        """Créer une réponse HTTP pour un fichier CSV"""
        
        def generate():
            yield csv_data
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_with_date = f"{filename}_{timestamp}.csv"
        
        return Response(
            generate(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename_with_date}"',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )

    @staticmethod
    def create_json_response(json_data, filename):
        """Créer une réponse HTTP pour un fichier JSON"""
        
        def generate():
            yield json_data
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_with_date = f"{filename}_{timestamp}.json"
        
        return Response(
            generate(),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename_with_date}"',
                'Content-Type': 'application/json; charset=utf-8'
            }
        )

    @staticmethod
    def create_hl7_response(hl7_data, filename):
        """Créer une réponse HTTP pour un fichier HL7"""
        
        def generate():
            yield hl7_data
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_with_date = f"{filename}_{timestamp}.hl7"
        
        return Response(
            generate(),
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename="{filename_with_date}"',
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )

# Instance globale du service
export_service = ExportService()
