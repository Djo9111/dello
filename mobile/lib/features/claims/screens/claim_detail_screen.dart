import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/network/api_exception.dart';
import '../data/claims_repository.dart';
import '../models/claim.dart';
import '../../reports/models/report.dart';

class ClaimDetailScreen extends StatefulWidget {
  const ClaimDetailScreen({
    super.key,
    required this.claim,
    required this.isReportOwner,
  });

  final Claim claim;

  /// Vrai si l'utilisateur est le déclarant du signalement (il décide),
  /// faux s'il est le demandeur (il attend ou répond).
  final bool isReportOwner;

  @override
  State<ClaimDetailScreen> createState() => _ClaimDetailScreenState();
}

class _ClaimDetailScreenState extends State<ClaimDetailScreen> {
  final _repository = ClaimsRepository();
  final _answerController = TextEditingController();

  late Claim _claim = widget.claim;
  Contact? _contact;
  bool _isBusy = false;
  bool _hasChanged = false;

  @override
  void dispose() {
    _answerController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<Claim> Function() action) async {
    setState(() => _isBusy = true);
    try {
      final claim = await action();
      if (mounted) {
        setState(() {
          _claim = claim;
          _hasChanged = true;
          _contact = null;
        });
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _loadContact() async {
    setState(() => _isBusy = true);
    try {
      final contact = await _repository.contact(_claim.id);
      if (mounted) setState(() => _contact = contact);
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _call(String phoneNumber) async {
    final uri = Uri(scheme: 'tel', path: phoneNumber);
    if (!await launchUrl(uri) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Impossible de lancer l\'appel')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final report = _claim.report;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_hasChanged);
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Demande')),
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [
                        Text(
              report.documentsLabel,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            Text('${report.kindLabel} · ${report.locationLabel}'),
            const SizedBox(height: 8),
            Chip(label: Text(_claim.status.label)),
            if (_claim.message != null) ...[
              const SizedBox(height: 12),
              Text('Message : ${_claim.message}'),
            ],
            const Divider(height: 32),
            if (_claim.isVerified) ..._buildContactSection(),
            if (_claim.isPending && widget.isReportOwner) ..._buildOwnerActions(),
            if (_claim.isPending && !widget.isReportOwner) ..._buildClaimantActions(report),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildContactSection() {
    if (_contact == null) {
      return [
        const Text(
          'Demande acceptée. Vous pouvez afficher le contact de l\'autre personne.',
          style: TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _isBusy ? null : _loadContact,
          icon: const Icon(Icons.contact_phone_outlined),
          label: const Text('Afficher le contact'),
        ),
      ];
    }

    return [
      Text(
        _contact!.fullName,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
      ),
      const SizedBox(height: 4),
      Text(_contact!.phoneNumber, style: const TextStyle(fontSize: 16)),
      const SizedBox(height: 16),
      FilledButton.icon(
        onPressed: () => _call(_contact!.phoneNumber),
        icon: const Icon(Icons.call),
        label: const Text('Appeler'),
      ),
      const SizedBox(height: 12),
      if (!widget.isReportOwner)
        OutlinedButton(
          onPressed: _isBusy ? null : () => _run(() => _repository.withdraw(_claim.id)),
          child: const Text('Annuler la mise en relation'),
        ),
    ];
  }

  List<Widget> _buildOwnerActions() {
    return [
      const Text(
        'Cette personne dit que le document lui appartient.',
        style: TextStyle(color: Colors.black54),
      ),
      if (_claim.answerAttempts > 0) ...[
        const SizedBox(height: 8),
        Text(
          'Réponses incorrectes à votre question : ${_claim.answerAttempts}',
          style: const TextStyle(fontSize: 13, color: Colors.black54),
        ),
      ],
      const SizedBox(height: 16),
      FilledButton(
        onPressed: _isBusy ? null : () => _run(() => _repository.approve(_claim.id)),
        child: const Text('Accepter et échanger les contacts'),
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: _isBusy ? null : () => _run(() => _repository.reject(_claim.id)),
        child: const Text('Refuser'),
      ),
    ];
  }

    List<Widget> _buildClaimantActions(Report report) {
    return [
      const Text(
        'En attente de la décision du déclarant.',
        style: TextStyle(color: Colors.black54),
      ),
      if (report.hasVerificationQuestion) ...[
        const SizedBox(height: 16),
        Text(report.verificationQuestion!),
        const SizedBox(height: 8),
        TextField(
          controller: _answerController,
          enabled: !_isBusy,
          autocorrect: false,
          decoration: const InputDecoration(labelText: 'Nouvelle réponse'),
        ),
        const SizedBox(height: 8),
        FilledButton(
          onPressed: _isBusy
              ? null
              : () => _run(
                    () => _repository.answerQuestion(
                      _claim.id,
                      _answerController.text.trim(),
                    ),
                  ),
          child: const Text('Envoyer ma réponse'),
        ),
      ],
      const SizedBox(height: 12),
      OutlinedButton(
        onPressed: _isBusy ? null : () => _run(() => _repository.withdraw(_claim.id)),
        child: const Text('Annuler ma demande'),
      ),
    ];
  }
}