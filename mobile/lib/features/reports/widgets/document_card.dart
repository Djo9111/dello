import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../models/report.dart';
import 'document_style.dart';

/// Représentation dessinée d'un document déclaré.
///
/// Les proportions suivent celles de la vraie pièce : format carte bancaire
/// pour les cartes, livret vertical pour le passeport. Le numéro n'est
/// jamais affiché, le serveur ne le renvoyant pas.
class DocumentCard extends StatelessWidget {
  const DocumentCard({
    super.key,
    required this.document,
    this.ownerNameMasked,
    this.region,
    this.occurredOn,
  });

  final ReportDocument document;
  final String? ownerNameMasked;
  final String? region;
  final DateTime? occurredOn;

  bool get _isBooklet => document.documentType == DocumentType.passeport;

  @override
  Widget build(BuildContext context) {
    final style = DocumentStyle.of(document.documentType);

    return AspectRatio(
      // 1.586 est le rapport d'une carte au format bancaire, 1.4 celui
      // d'un livret ouvert à plat.
      aspectRatio: _isBooklet ? 1.4 : 1.586,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: style.color.withValues(alpha: 0.35)),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              style.color.withValues(alpha: 0.07),
              style.color.withValues(alpha: 0.02),
            ],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Header(style: style, type: document.documentType),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                child: _isBooklet ? _buildBooklet(style) : _buildCard(style),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard(DocumentStyle style) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PhotoPlaceholder(color: style.color),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _Field(label: 'Nom', value: ownerNameMasked ?? 'Non précisé'),
              _Field(label: 'Lieu', value: region ?? 'Non précisé'),
              _NumberField(hasNumber: document.hasDocumentNumber, color: style.color),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBooklet(DocumentStyle style) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _PhotoPlaceholder(color: style.color, height: 70),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Field(label: 'Nom', value: ownerNameMasked ?? 'Non précisé'),
                  const SizedBox(height: 10),
                  _Field(label: 'Lieu', value: region ?? 'Non précisé'),
                ],
              ),
            ),
          ],
        ),
        const Spacer(),
        // La bande de lecture optique, signature visuelle d'un passeport
        Container(
          height: 26,
          decoration: BoxDecoration(
            color: style.color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(6),
          ),
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Text(
            document.hasDocumentNumber
                ? 'P<SEN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'
                : 'P<SEN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<',
            maxLines: 1,
            overflow: TextOverflow.clip,
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 11,
              letterSpacing: 1,
              color: style.color.withValues(alpha: 0.55),
            ),
          ),
        ),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.style, required this.type});

  final DocumentStyle style;
  final DocumentType type;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
      decoration: BoxDecoration(
        color: style.color,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(13)),
      ),
      child: Row(
        children: [
          Icon(style.icon, size: 16, color: Colors.white),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              type.label.toUpperCase(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
          ),
          Text(
            'SÉNÉGAL',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.75),
              fontSize: 10,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

/// Emplacement de la photo. Volontairement vide : Dello ne stocke aucune
/// image de document.
class _PhotoPlaceholder extends StatelessWidget {
  const _PhotoPlaceholder({required this.color, this.height = 62});

  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: height * 0.78,
      height: height,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.20)),
      ),
      child: Icon(
        Icons.person_outline,
        color: color.withValues(alpha: 0.35),
        size: height * 0.42,
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            fontSize: 8,
            letterSpacing: 0.8,
            color: AppTheme.inkSoft,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 1),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: AppTheme.ink,
          ),
        ),
      ],
    );
  }
}

/// Le numéro n'est jamais renvoyé par le serveur : seule sa présence est
/// connue, et c'est elle qui conditionne le rapprochement automatique.
class _NumberField extends StatelessWidget {
  const _NumberField({required this.hasNumber, required this.color});

  final bool hasNumber;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'NUMÉRO',
          style: TextStyle(
            fontSize: 8,
            letterSpacing: 0.8,
            color: AppTheme.inkSoft,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        Row(
          children: [
            Text(
              hasNumber ? '•••• •••• ••••' : 'Non renseigné',
              style: TextStyle(
                fontSize: hasNumber ? 14 : 12,
                letterSpacing: hasNumber ? 2 : 0,
                fontWeight: FontWeight.w700,
                color: hasNumber ? AppTheme.ink : AppTheme.inkSoft,
              ),
            ),
            if (hasNumber) ...[
              const SizedBox(width: 8),
              Icon(Icons.lock_outline, size: 12, color: color),
            ],
          ],
        ),
      ],
    );
  }
}