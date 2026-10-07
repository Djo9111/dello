import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../../claims/data/claims_repository.dart';
import '../models/report.dart';
import '../widgets/documents_section.dart';

class ReportPublicDetailScreen extends StatefulWidget {
  const ReportPublicDetailScreen({super.key, required this.report});

  final Report report;

  @override
  State<ReportPublicDetailScreen> createState() => _ReportPublicDetailScreenState();
}

class _ReportPublicDetailScreenState extends State<ReportPublicDetailScreen> {
  final _repository = ClaimsRepository();
  final _answerController = TextEditingController();
  final _messageController = TextEditingController();

  bool _isSubmitting = false;
  String? _error;

  @override
  void dispose() {
    _answerController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final claim = await _repository.claimReport(
        widget.report.id,
        message: _messageController.text.trim().isEmpty
            ? null
            : _messageController.text.trim(),
        answer: _answerController.text.trim().isEmpty
            ? null
            : _answerController.text.trim(),
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            claim.isVerified
                ? 'Demande acceptée. Le contact est disponible.'
                : 'Demande envoyée. Le déclarant doit la valider.',
          ),
        ),
      );
      Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final report = widget.report;

    return Scaffold(
      appBar: AppBar(title: const Text('Signalement')),
      body: ListView(
        padding: const EdgeInsets.all(20),
                children: [
          Text(
            report.documentsLabel,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text('${report.kindLabel} · ${report.locationLabel}'),
          const SizedBox(height: 20),
          DocumentsSection(report: report),
          const Divider(height: 32),
                    Text(
            report.claimPrompt,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
          ),
          const SizedBox(height: 16),
          if (report.hasVerificationQuestion) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(report.verificationQuestion!),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _answerController,
              enabled: !_isSubmitting,
              autocorrect: false,
              decoration: const InputDecoration(labelText: 'Votre réponse'),
            ),
            const SizedBox(height: 16),
          ],
          TextField(
            controller: _messageController,
            enabled: !_isSubmitting,
            maxLines: 3,
            maxLength: 300,
            decoration: const InputDecoration(
              labelText: 'Message (optionnel)',
              alignLabelWithHint: true,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(_error!),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _isSubmitting ? null : _submit,
            child: _isSubmitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : Text(report.claimAction),
          ),
        ],
      ),
    );
  }
}