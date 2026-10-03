import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../models/report.dart';
import 'document_style.dart';

/// Carte du carrousel : format large, lisible d'un coup d'oeil.
class ReportCarouselCard extends StatelessWidget {
  const ReportCarouselCard({super.key, required this.report, this.onTap});

  final Report report;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final style = DocumentStyle.of(report.mainDocumentType);
    final isFound = report.kind == ReportKind.found;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: style.color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(style.icon, color: style.color, size: 22),
                  ),
                  const Spacer(),
                  _KindBadge(isFound: isFound, label: report.kindLabel),
                ],
              ),
              const Spacer(),
              Text(
                report.ownerNameMasked ?? report.documentsLabel,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.ink,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                report.documentsLabel,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, color: AppTheme.inkSoft),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.place_outlined, size: 14, color: AppTheme.inkSoft),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      report.locationLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13, color: AppTheme.inkSoft),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Ligne des listes verticales.
class ReportRow extends StatelessWidget {
  const ReportRow({super.key, required this.report, this.onTap, this.trailing});

  final Report report;
  final VoidCallback? onTap;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final style = DocumentStyle.of(report.mainDocumentType);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: ListTile(
          onTap: onTap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          leading: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: style.color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(style.icon, color: style.color, size: 22),
          ),
          title: Text(
            report.ownerNameMasked ?? report.documentsLabel,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Les familles de documents du signalement, pour qu'un sac
                // volé ne se résume pas à sa première pièce
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: report.documents
                      .map((document) => _DocumentChip(type: document.documentType))
                      .toList(),
                ),
                const SizedBox(height: 6),
                Text(
                  '${report.locationLabel} · ${report.kindLabel}',
                  style: const TextStyle(fontSize: 13, color: AppTheme.inkSoft),
                ),
              ],
            ),
          ),
          trailing: trailing ??
              _KindBadge(
                isFound: report.kind == ReportKind.found,
                label: report.kindLabel,
              ),
        ),
      ),
    );
  }
}

class _DocumentChip extends StatelessWidget {
  const _DocumentChip({required this.type});

  final DocumentType type;

  @override
  Widget build(BuildContext context) {
    final style = DocumentStyle.of(type);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: style.color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(style.icon, size: 12, color: style.color),
          const SizedBox(width: 4),
          Text(
            type.label,
            style: TextStyle(fontSize: 11, color: style.color, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _KindBadge extends StatelessWidget {
  const _KindBadge({required this.isFound, required this.label});

  final bool isFound;
  final String label;

  @override
  Widget build(BuildContext context) {
    final color = isFound ? AppTheme.success : AppTheme.accent;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color),
      ),
    );
  }
}