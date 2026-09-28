import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/report_tile.dart';

class ReportDetailScreen extends StatefulWidget {
  const ReportDetailScreen({super.key, required this.reportId});

  final String reportId;

  @override
  State<ReportDetailScreen> createState() => _ReportDetailScreenState();
}

class _ReportDetailScreenState extends State<ReportDetailScreen> {
  final _repository = ReportsRepository();

  Report? _report;
  List<Report> _matches = [];
  bool _isLoading = true;
  bool _hasChanged = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);

    try {
      final report = await _repository.getMine(widget.reportId);
      final matches = report.hasDocumentNumber == true
          ? await _repository.matches(widget.reportId)
          : <Report>[];

      if (mounted) {
        setState(() {
          _report = report;
          _matches = matches;
          _error = null;
        });
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _togglePublication(bool value) async {
    try {
      final updated = await _repository.update(widget.reportId, isPublished: value);
      if (mounted) {
        setState(() {
          _report = updated;
          _hasChanged = true;
        });
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _confirmDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Supprimer cette déclaration ?'),
        content: const Text('Cette action est définitive.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await _repository.remove(widget.reportId);
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_hasChanged);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Ma déclaration'),
          actions: [
            IconButton(
              tooltip: 'Supprimer',
              icon: const Icon(Icons.delete_outline),
              onPressed: _isLoading ? null : _confirmDelete,
            ),
          ],
        ),
        body: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text(_error!));

    final report = _report!;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          report.documentType.label,
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text('${report.kind.label} · ${report.status.label}'),
        const SizedBox(height: 20),
        _InfoRow(label: 'Nom masqué', value: report.ownerNameMasked ?? 'Non renseigné'),
        _InfoRow(label: 'Lieu', value: report.locationLabel),
        _InfoRow(label: 'Lieu précis', value: report.placeDetail ?? 'Non renseigné'),
        _InfoRow(
          label: 'Numéro enregistré',
          value: report.hasDocumentNumber == true ? 'Oui' : 'Non',
        ),
        const Divider(height: 32),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Visible par les autres utilisateurs'),
          value: report.isPublished ?? true,
          onChanged: _togglePublication,
        ),
        const Divider(height: 32),
        Text(
          'Correspondances',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 4),
        Text(
          report.hasDocumentNumber == true
              ? 'Signalements portant le même numéro de document.'
              : 'Ajoutez le numéro du document pour activer le rapprochement automatique.',
          style: const TextStyle(color: Colors.black54, fontSize: 13),
        ),
        const SizedBox(height: 12),
        if (_matches.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('Aucune correspondance pour le moment.'),
          )
        else
                ..._matches.map((match) => ReportRow(report: match)),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}