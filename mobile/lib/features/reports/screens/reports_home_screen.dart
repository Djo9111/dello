import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/document_style.dart';
import '../widgets/family_carousel.dart';
import 'report_public_detail_screen.dart';
import 'reports_family_screen.dart';

class ReportsHomeScreen extends StatefulWidget {
  const ReportsHomeScreen({super.key});

  @override
  State<ReportsHomeScreen> createState() => _ReportsHomeScreenState();
}

class _ReportsHomeScreenState extends State<ReportsHomeScreen> {
  static const _previewSize = 10;

  final _repository = ReportsRepository();

  Map<DocumentType, List<Report>> _byFamily = {};
  ReportKind? _kind;
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
      // Une requête par famille, lancées ensemble : chaque ligne reste
      // remplie même si une famille n'a que des signalements anciens.
      final results = await Future.wait(
        DocumentType.values.map(
          (type) => _repository.listPublic(
            kind: _kind,
            documentType: type,
            limit: _previewSize,
          ),
        ),
      );

      final grouped = <DocumentType, List<Report>>{};
      for (var i = 0; i < DocumentType.values.length; i++) {
        if (results[i].isNotEmpty) grouped[DocumentType.values[i]] = results[i];
      }

      if (mounted) setState(() => _byFamily = grouped);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _openReport(Report report) async {
    final claimed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => ReportPublicDetailScreen(report: report)),
    );
    if (claimed == true) _load();
  }

  Future<void> _openFamily(DocumentType type) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ReportsFamilyScreen(documentType: type, kind: _kind),
      ),
    );
    if (changed == true) _load();
  }

  void _setKind(ReportKind? kind) {
    setState(() => _kind = kind);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
          child: Row(
            children: [
              _FilterPill(
                label: 'Tout',
                selected: _kind == null,
                onTap: () => _setKind(null),
              ),
              const SizedBox(width: 8),
              _FilterPill(
                label: 'Perdus',
                selected: _kind == ReportKind.lost,
                onTap: () => _setKind(ReportKind.lost),
              ),
              const SizedBox(width: 8),
              _FilterPill(
                label: 'Trouvés',
                selected: _kind == ReportKind.found,
                onTap: () => _setKind(ReportKind.found),
              ),
            ],
          ),
        ),
        Expanded(child: _buildBody()),
      ],
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());

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

    if (_byFamily.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Text(
            'Aucun signalement pour le moment.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppTheme.inkSoft),
          ),
        ),
      );
    }

    final families = _byFamily.keys.toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.only(bottom: 24),
        itemCount: families.length,
        itemBuilder: (context, index) {
          final type = families[index];
          final reports = _byFamily[type]!;
          final style = DocumentStyle.of(type);

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 8, 10),
                child: Row(
                  children: [
                    Icon(style.icon, size: 20, color: style.color),
                    const SizedBox(width: 8),
                    Text(
                      type.label,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.ink,
                      ),
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => _openFamily(type),
                      child: const Text('Tout voir'),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(left: 16),
                child: FamilyCarousel(reports: reports, onReportTap: _openReport),
              ),
              const SizedBox(height: 16),
            ],
          );
        },
      ),
    );
  }
}

class _FilterPill extends StatelessWidget {
  const _FilterPill({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primary : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? AppTheme.primary : const Color(0xFFE0DAD0),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : AppTheme.ink,
            fontWeight: FontWeight.w600,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}