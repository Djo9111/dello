import 'package:flutter/material.dart';

import '../../../core/location/location_service.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/document_style.dart';

class ReportFormScreen extends StatefulWidget {
  const ReportFormScreen({super.key});

  @override
  State<ReportFormScreen> createState() => _ReportFormScreenState();
}

class _ReportFormScreenState extends State<ReportFormScreen> {
  static const _maxDocuments = 10;

  final _repository = ReportsRepository();
  final _ownerNameController = TextEditingController();
  final _communeController = TextEditingController();
  final _placeController = TextEditingController();
  final _questionController = TextEditingController();
  final _answerController = TextEditingController();

  /// Un incident, plusieurs documents : un sac contient souvent la carte
  /// d'identité et le permis.
  final List<DocumentDraft> _documents = [
    DocumentDraft(documentType: DocumentType.cni),
  ];
  final List<TextEditingController> _numberControllers = [
    TextEditingController(),
  ];

  ReportKind _kind = ReportKind.lost;
  ReportCircumstance _circumstance = ReportCircumstance.lost;
  String _region = senegalRegions.first;
  DateTime? _occurredOn;

  double? _latitude;
  double? _longitude;
  bool _isLocating = false;

  bool _isSubmitting = false;
  String? _generalError;
  Map<String, String> _fieldErrors = {};

  @override
  void dispose() {
    _ownerNameController.dispose();
    _communeController.dispose();
    _placeController.dispose();
    _questionController.dispose();
    _answerController.dispose();
    for (final controller in _numberControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  void _addDocument() {
    if (_documents.length >= _maxDocuments) return;

    setState(() {
      _documents.add(DocumentDraft(documentType: DocumentType.autre));
      _numberControllers.add(TextEditingController());
    });
  }

  void _removeDocument(int index) {
    if (_documents.length == 1) return;

    setState(() {
      _documents.removeAt(index);
      _numberControllers.removeAt(index).dispose();
    });
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

  /// Position proposée uniquement pour un document trouvé : le déclarant
  /// est alors sur place. Pour une perte, la position actuelle serait
  /// souvent le domicile, donc une information fausse et sensible.
  Future<void> _useCurrentPosition() async {
    setState(() => _isLocating = true);

    try {
      final position = await LocationService.currentPosition();
      if (position != null && mounted) {
        setState(() {
          _latitude = position.latitude;
          _longitude = position.longitude;
        });
      }
    } on LocationFailure catch (failure) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(failure.message)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Position indisponible')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLocating = false);
    }
  }

  Future<void> _submit() async {
    if (_isSubmitting) return;

    setState(() {
      _isSubmitting = true;
      _generalError = null;
      _fieldErrors = {};
    });

    for (var i = 0; i < _documents.length; i++) {
      _documents[i].documentNumber = _numberControllers[i].text;
    }

    try {
      await _repository.create(
        kind: _kind,
        documents: _documents,
        region: _region,
        circumstance: _kind == ReportKind.lost ? _circumstance : null,
        ownerName: _ownerNameController.text.trim(),
        commune: _communeController.text.trim(),
        placeDetail: _placeController.text.trim(),
        occurredOn: _occurredOn,
        latitude: _kind == ReportKind.found ? _latitude : null,
        longitude: _kind == ReportKind.found ? _longitude : null,
        verificationQuestion: _questionController.text.trim(),
        verificationAnswer: _answerController.text.trim(),
      );

      // Les numéros ne restent pas en mémoire après l'envoi
      for (final controller in _numberControllers) {
        controller.clear();
      }
      _answerController.clear();

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
              if (_kind == ReportKind.lost) ...[
                const SizedBox(height: 12),
                SegmentedButton<ReportCircumstance>(
                  segments: const [
                    ButtonSegment(
                      value: ReportCircumstance.lost,
                      label: Text('Égaré'),
                    ),
                    ButtonSegment(
                      value: ReportCircumstance.stolen,
                      label: Text('Volé'),
                    ),
                  ],
                  selected: {_circumstance},
                  onSelectionChanged: _isSubmitting
                      ? null
                      : (selection) =>
                          setState(() => _circumstance = selection.first),
                ),
              ],
              const SizedBox(height: 24),
              Row(
                children: [
                  const Text(
                    'Documents concernés',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                  const Spacer(),
                  if (_documents.length < _maxDocuments)
                    TextButton.icon(
                      onPressed: _isSubmitting ? null : _addDocument,
                      icon: const Icon(Icons.add, size: 18),
                      label: const Text('Ajouter'),
                    ),
                ],
              ),
              const Text(
                'Un sac contient souvent plusieurs papiers : ajoutez-les tous.',
                style: TextStyle(fontSize: 12, color: AppTheme.inkSoft),
              ),
              const SizedBox(height: 12),
              ...List.generate(_documents.length, _buildDocumentCard),
              const SizedBox(height: 20),
              TextField(
                controller: _ownerNameController,
                textCapitalization: TextCapitalization.words,
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Nom inscrit sur les documents (optionnel)',
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
              if (_kind == ReportKind.found) ...[
                OutlinedButton.icon(
                  onPressed:
                      _isLocating || _isSubmitting ? null : _useCurrentPosition,
                  icon: _isLocating
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          _latitude == null ? Icons.my_location : Icons.check,
                          color: _latitude == null ? null : AppTheme.success,
                        ),
                  label: Text(
                    _latitude == null
                        ? 'Enregistrer ma position actuelle'
                        : 'Position enregistrée',
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Visible par vous seul. Utile car vous êtes sur place.',
                  style: TextStyle(fontSize: 12, color: AppTheme.inkSoft),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _questionController,
                  enabled: !_isSubmitting,
                  maxLength: 200,
                  decoration: InputDecoration(
                    labelText: 'Question de vérification (optionnel)',
                    helperText: 'Par exemple : date de naissance sur la carte ?',
                    helperMaxLines: 2,
                    prefixIcon: const Icon(Icons.help_outline),
                    errorText: _fieldErrors['verification_question'],
                  ),
                ),
                TextField(
                  controller: _answerController,
                  enabled: !_isSubmitting,
                  autocorrect: false,
                  maxLength: 100,
                  decoration: InputDecoration(
                    labelText: 'Réponse attendue',
                    helperText: 'Une bonne réponse débloque la mise en relation.',
                    helperMaxLines: 2,
                    prefixIcon: const Icon(Icons.key_outlined),
                    errorText: _fieldErrors['verification_answer'],
                  ),
                ),
                const SizedBox(height: 8),
              ],
              OutlinedButton.icon(
                onPressed: _isSubmitting ? null : _pickDate,
                icon: const Icon(Icons.calendar_today_outlined),
                label: Text(dateLabel),
              ),
              if (_generalError != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(12),
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

  Widget _buildDocumentCard(int index) {
    final document = _documents[index];
    final style = DocumentStyle.of(document.documentType);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 8, 16),
          child: Column(
            children: [
              Row(
                children: [
                  Icon(style.icon, size: 20, color: style.color),
                  const SizedBox(width: 10),
                  Expanded(
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<DocumentType>(
                        value: document.documentType,
                        isExpanded: true,
                        items: DocumentType.values
                            .map((type) => DropdownMenuItem(
                                  value: type,
                                  child: Text(type.label),
                                ))
                            .toList(),
                        onChanged: _isSubmitting
                            ? null
                            : (value) =>
                                setState(() => document.documentType = value!),
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Retirer',
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: _documents.length == 1 || _isSubmitting
                        ? null
                        : () => _removeDocument(index),
                  ),
                ],
              ),
              TextField(
                controller: _numberControllers[index],
                enabled: !_isSubmitting,
                decoration: InputDecoration(
                  labelText: 'Numéro (optionnel)',
                  helperText: 'Permet le rapprochement automatique',
                  prefixIcon: const Icon(Icons.pin_outlined),
                  errorText: _fieldErrors['documents.$index.document_number'],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}