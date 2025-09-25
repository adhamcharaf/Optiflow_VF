"""
Module pour la génération de bons de commande PDF
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from datetime import datetime, timedelta
import io
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_order_pdf(
    product_name: str,
    product_id: str,
    stock_at_order: int,
    alert_type: str,
    quantity_ordered: int,
    unit_price: float,
    lead_time_days: int = 5,
    order_date: datetime = None
) -> bytes:
    """
    Génère un bon de commande PDF simple

    Args:
        product_name: Nom du produit
        product_id: ID du produit
        stock_at_order: Stock au moment de la commande
        alert_type: Type d'alerte (CRITIQUE/ATTENTION)
        quantity_ordered: Quantité commandée
        unit_price: Prix unitaire
        lead_time_days: Délai de livraison en jours
        order_date: Date de la commande (par défaut: maintenant)

    Returns:
        bytes: Contenu du PDF en bytes
    """
    try:
        # Buffer pour stocker le PDF
        buffer = io.BytesIO()

        # Créer le document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=20,
            alignment=TA_CENTER
        )

        # Date de commande
        if order_date is None:
            order_date = datetime.now()

        # Calculer la date de livraison prévue
        expected_delivery = order_date + timedelta(days=lead_time_days)

        # Calculer le total
        total_amount = quantity_ordered * unit_price

        # Titre
        story.append(Paragraph("BON DE COMMANDE OPTIFLOW", title_style))
        story.append(Spacer(1, 5*mm))

        # Ligne de séparation décorative
        story.append(Paragraph("=" * 60, subtitle_style))
        story.append(Spacer(1, 5*mm))

        # Informations de base
        info_data = [
            ['Date de commande:', order_date.strftime("%d/%m/%Y %H:%M")],
            ['Référence produit:', f"{product_id}"],
            ['', ''],  # Ligne vide pour l'espacement
        ]

        info_table = Table(info_data, colWidths=[100*mm, 80*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#34495e')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10*mm))

        # Détails de la commande
        details_data = [
            ['Détails de la commande', ''],
            ['', ''],
            ['Produit:', product_name],
            ['Stock actuel:', f"{stock_at_order} unités"],
            ['Type d\'alerte:', alert_type],
            ['', ''],
            ['Quantité commandée:', f"{quantity_ordered} unités"],
            ['Prix unitaire:', f"{unit_price:,.0f} FCFA"],
            ['', ''],
            ['Délai de livraison:', f"{lead_time_days} jours"],
            ['Livraison prévue:', expected_delivery.strftime("%d/%m/%Y")],
        ]

        # Définir les couleurs selon le type d'alerte
        alert_color = colors.red if alert_type == "CRITIQUE" else colors.orange

        details_table = Table(details_data, colWidths=[100*mm, 80*mm])
        details_table.setStyle(TableStyle([
            # Style général
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),

            # Titre de section
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 13),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#2c3e50')),
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),

            # Labels en gras
            ('FONTNAME', (0, 2), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 2), (0, -1), colors.HexColor('#34495e')),

            # Coloration du type d'alerte
            ('TEXTCOLOR', (1, 4), (1, 4), alert_color),
            ('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 15*mm))

        # Ligne de séparation
        story.append(Paragraph("=" * 60, subtitle_style))
        story.append(Spacer(1, 5*mm))

        # Total
        total_data = [
            ['TOTAL:', f'{total_amount:,.0f} FCFA'],
        ]

        total_table = Table(total_data, colWidths=[100*mm, 80*mm])
        total_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#27ae60')),
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(total_table)
        story.append(Spacer(1, 5*mm))

        # Ligne de séparation finale
        story.append(Paragraph("=" * 60, subtitle_style))

        # Note de bas de page
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#95a5a6'),
            alignment=TA_CENTER,
            spaceBefore=20
        )
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph("Document généré automatiquement par Optiflow", footer_style))
        story.append(Paragraph(f"© {datetime.now().year} Système de Gestion Intelligente des Stocks", footer_style))

        # Construire le PDF
        doc.build(story)

        # Récupérer le contenu du PDF
        pdf_content = buffer.getvalue()
        buffer.close()

        logger.info(f"PDF généré avec succès pour le produit {product_id}")
        return pdf_content

    except Exception as e:
        logger.error(f"Erreur lors de la génération du PDF: {e}")
        raise

def test_pdf_generation():
    """Fonction de test pour vérifier la génération de PDF"""
    try:
        pdf_bytes = generate_order_pdf(
            product_name="Climatiseur Split 12000 BTU",
            product_id="1",
            stock_at_order=15,
            alert_type="CRITIQUE",
            quantity_ordered=100,
            unit_price=349377.28,
            lead_time_days=5
        )

        # Sauvegarder le PDF de test
        with open("test_bon_commande.pdf", "wb") as f:
            f.write(pdf_bytes)

        print("PDF de test généré avec succès: test_bon_commande.pdf")
        return True

    except Exception as e:
        print(f"Erreur lors du test: {e}")
        return False

if __name__ == "__main__":
    test_pdf_generation()