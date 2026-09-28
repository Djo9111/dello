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
    final style = DocumentStyle.of(report.documentType);
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
                  _KindBadge(isFound: isFound),
                ],
              ),
              const Spacer(),
              Text(
                report.ownerNameMasked ?? report.documentType.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.ink,
                ),
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
              if (report.hasVerificationQuestion) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.verified_user_outlined,
                        size: 14, color: AppTheme.success),
                    const SizedBox(width: 4),
                    const Text(
                      'Vérification immédiate possible',
                      style: TextStyle(fontSize: 12, color: AppTheme.success),
                    ),
                  ],
                ),
              ],
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
    final style = DocumentStyle.of(report.documentType);

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
            report.ownerNameMasked ?? report.documentType.label,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Text(
              '${report.locationLabel} · ${report.kind.label}',
              style: const TextStyle(fontSize: 13, color: AppTheme.inkSoft),
            ),
          ),
          trailing: trailing ?? _KindBadge(isFound: report.kind == ReportKind.found),
        ),
      ),
    );
  }
}

class _KindBadge extends StatelessWidget {
  const _KindBadge({required this.isFound});

  final bool isFound;

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
        isFound ? 'Trouvé' : 'Perdu',
        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: color),
      ),
    );
  }
}