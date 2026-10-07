import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../models/report.dart';
import 'document_card.dart';

class DocumentsSection extends StatelessWidget {
  const DocumentsSection({super.key, required this.report, this.showHint = true});

  final Report report;
  final bool showHint;

  @override
  Widget build(BuildContext context) {
    final count = report.documents.length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              count > 1 ? '$count documents' : 'Document',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
            const Spacer(),
            if (report.hasAnyDocumentNumber)
              const Row(
                children: [
                  Icon(Icons.verified_user_outlined,
                      size: 14, color: AppTheme.success),
                  SizedBox(width: 4),
                  Text(
                    'Rapprochement actif',
                    style: TextStyle(fontSize: 12, color: AppTheme.success),
                  ),
                ],
              ),
          ],
        ),
        const SizedBox(height: 12),
                ...report.documents.map(
          (document) => Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: DocumentCard(
              document: document,
              ownerNameMasked: report.ownerNameMasked,
              region: report.locationLabel,
              occurredOn: report.occurredOn,
            ),
          ),
        ),
      ],
    );
  }
}