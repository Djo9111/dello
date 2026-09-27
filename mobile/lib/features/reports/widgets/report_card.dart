import 'package:flutter/material.dart';

import '../models/report.dart';

class ReportCard extends StatelessWidget {
  const ReportCard({super.key, required this.report, this.onTap, this.trailing});

  final Report report;
  final VoidCallback? onTap;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isLost = report.kind == ReportKind.lost;

    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outlineVariant),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor:
              isLost ? scheme.errorContainer : scheme.primaryContainer,
          child: Icon(
            isLost ? Icons.search_off : Icons.inventory_2_outlined,
            size: 20,
            color: isLost ? scheme.onErrorContainer : scheme.onPrimaryContainer,
          ),
        ),
        title: Text(
          report.documentType.label,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (report.ownerNameMasked != null) Text(report.ownerNameMasked!),
            Text(report.locationLabel),
            Text(
              '${report.kind.label} · ${report.status.label}',
              style: TextStyle(fontSize: 12, color: scheme.outline),
            ),
          ],
        ),
        trailing: trailing,
      ),
    );
  }
}