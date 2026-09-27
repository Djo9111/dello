import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';

class ReportFormScreen extends StatefulWidget {
  const ReportFormScreen({super.key});

  @override
  State<ReportFormScreen> createState() => _ReportFormScreenState();
}

class _ReportFormScreenState extends State<ReportFormScreen> {
  final _repository = ReportsRepository();
  final _numberController = TextEditingController();
  final _ownerNameController = TextEditingController();
  final _communeController = TextEditingController();
  final _placeController = TextEditingController();

  ReportKind _kind = ReportKind.lost;
  DocumentType _documentType = DocumentType.cni;
  String _region = senegalRegions.first;
  DateTime? _occurredOn;

  bool _isSubmitting = false;
  String? _generalError;
  Map<String, String> _fieldErrors = {};

  @override
  void dispose() {
    _numberController.dispose();
    _ownerNameController.dispose();
    _communeController.dispose();
    _placeController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _occurredOn ?? now,
      firstDate: DateTime(now.year - 3),
      lastDate: now,
      helpText: 'Date de la perte ou de la découverte',
    );
    if (picked != null) setState(() => _occurredOn = picked);
  }

  Future<void> _submit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
      _generalError = null;
      _fieldErrors = {};
    });

    try {
      await _repository.create(
        kind: _kind,
        documentType: _documentType,
        region: _region,
        documentNumber: _numberController.text.trim(),
        ownerName: _ownerNameController.text.trim(),
        commune: _communeController.text.trim(),
        placeDetail: _placeController.text.trim(),
        occurredOn: _occurredOn,
      );

      // Le numéro ne reste pas en mémoire après l'envoi
      _numberController.clear();

      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _generalError = error.fieldErrors.isEmpty ? error.message : null;
        _fieldErrors = error.fieldErrors;
      });
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateLabel = _occurredOn == null
        ? 'Choisir une date (optionnel)'
        : '${_occurredOn!.day}/${_occurredOn!.month}/${_occurredOn!.year}';

    return Scaffold(
      appBar: AppBar(title: const Text('Nouvelle déclaration')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SegmentedButton<ReportKind>(
                segments: const [
                  ButtonSegment(
                    value: ReportKind.lost,
                    label: Text("J'ai perdu"),
                    icon: Icon(Icons.search_off),
                  ),
                  ButtonSegment(
                    value: ReportKind.found,
                    label: Text("J'ai trouvé"),
                    icon: Icon(Icons.inventory_2_outlined),
                  ),
                ],
                selected: {_kind},
                onSelectionChanged: _isSubmitting
                    ? null
                    : (selection) => setState(() => _kind = selection.first),
              ),
              const SizedBox(height: 20),
              DropdownButtonFormField<DocumentType>(
                initialValue: _documentType,
                decoration: const InputDecoration(labelText: 'Type de document'),
                items: DocumentType.values
                    .map((type) => DropdownMenuItem(
                          value: type,
                          child: Text(type.label),
                        ))
                    .toList(),
                onChanged: _isSubmitting
                    ? null
                    : (value) => setState(() => _documentType = value!),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _numberController,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Numéro du document (optionnel)',
                  helperText:
                      'Permet le rapprochement automatique. Jamais conservé en clair.',
                  helperMaxLines: 2,
                  prefixIcon: const Icon(Icons.pin_outlined),
                  errorText: _fieldErrors['document_number'],
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _ownerNameController,
                textCapitalization: TextCapitalization.words,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Nom inscrit sur le document (optionnel)',
                  helperText: 'Affiché masqué, par exemple Mod... G...',
                  helperMaxLines: 2,
                  prefixIcon: const Icon(Icons.person_outline),
                  errorText: _fieldErrors['owner_name'],
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _region,
                decoration: const InputDecoration(labelText: 'Région'),
                items: senegalRegions
                    .map((region) =>
                        DropdownMenuItem(value: region, child: Text(region)))
                    .toList(),
                onChanged: _isSubmitting
                    ? null
                    : (value) => setState(() => _region = value!),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _communeController,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Commune (optionnel)',
                  prefixIcon: const Icon(Icons.location_city_outlined),
                  errorText: _fieldErrors['commune'],
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _placeController,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Lieu précis (optionnel)',
                  helperText: 'Visible par vous seul',
                  prefixIcon: const Icon(Icons.place_outlined),
                  errorText: _fieldErrors['place_detail'],
                ),
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _isSubmitting ? null : _pickDate,
                icon: const Icon(Icons.calendar_today_outlined),
                label: Text(dateLabel),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(50),
                ),
              ),
              if (_generalError != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(_generalError!),
                ),
              ],
              const SizedBox(height: 24),
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
                    : const Text('Publier la déclaration'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}