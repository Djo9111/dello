import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/report_card.dart';

class ReportsListScreen extends StatefulWidget {
  const ReportsListScreen({super.key});

  @override
  State<ReportsListScreen> createState() => _ReportsListScreenState();
}

class _ReportsListScreenState extends State<ReportsListScreen> {
  final _repository = ReportsRepository();

  List<Report> _reports = [];
  ReportKind? _kind;
  DocumentType? _documentType;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final reports = await _repository.listPublic(
        kind: _kind,
        documentType: _documentType,
      );
      if (mounted) setState(() => _reports = reports);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              FilterChip(
                label: const Text('Perdus'),
                selected: _kind == ReportKind.lost,
                onSelected: (selected) {
                  setState(() => _kind = selected ? ReportKind.lost : null);
                  _load();
                },
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: const Text('Trouvés'),
                selected: _kind == ReportKind.found,
                onSelected: (selected) {
                  setState(() => _kind = selected ? ReportKind.found : null);
                  _load();
                },
              ),
              const SizedBox(width: 8),
              ...DocumentType.values.take(3).map(
                    (type) => Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(type.label),
                        selected: _documentType == type,
                        onSelected: (selected) {
                          setState(() => _documentType = selected ? type : null);
                          _load();
                        },
                      ),
                    ),
                  ),
            ],
          ),
        ),
        Expanded(child: _buildBody()),
      ],
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('Réessayer')),
          ],
        ),
      );
    }

    if (_reports.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Text(
            'Aucun signalement pour ces critères.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        itemCount: _reports.length,
        itemBuilder: (context, index) => ReportCard(report: _reports[index]),
      ),
    );
  }
}