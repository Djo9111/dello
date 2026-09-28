import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/document_style.dart';
import '../widgets/family_carousel.dart';
import '../widgets/report_tile.dart';
import 'report_public_detail_screen.dart';
import 'reports_family_screen.dart';

class ReportsHomeScreen extends StatefulWidget {
  const ReportsHomeScreen({super.key});

  @override
  State<ReportsHomeScreen> createState() => _ReportsHomeScreenState();
}

class _ReportsHomeScreenState extends State<ReportsHomeScreen> {
  static const _previewSize = 10;
  static const _searchDebounce = Duration(milliseconds: 450);

  final _repository = ReportsRepository();
  final _searchController = TextEditingController();

  Timer? _debounce;
  Map<DocumentType, List<Report>> _byFamily = {};
  List<Report> _searchResults = [];
  String _search = '';
  ReportKind? _kind;
  bool _isLoading = true;
  String? _error;

  bool get _isSearching => _search.length >= 2;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  /// Attente avant l'appel : sans cela, une requête partirait à chaque
  /// lettre tapée, et les réponses pourraient revenir dans le désordre.
  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(_searchDebounce, () {
      setState(() => _search = value.trim());
      _load();
    });
  }

  void _clearSearch() {
    _debounce?.cancel();
    _searchController.clear();
    setState(() => _search = '');
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (_isSearching) {
        final results = await _repository.listPublic(
          kind: _kind,
          search: _search,
          limit: 50,
        );
        if (mounted) setState(() => _searchResults = results);
      } else {
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
      }
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
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
          child: TextField(
            controller: _searchController,
            onChanged: _onSearchChanged,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Numéro du document, commune, nom...',
              prefixIcon: const Icon(Icons.search, color: AppTheme.inkSoft),
              suffixIcon: _searchController.text.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: _clearSearch,
                    ),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
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

    if (_isSearching) return _buildSearchResults();

    if (_byFamily.isEmpty) {
      return const _EmptyState(message: 'Aucun signalement pour le moment.');
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

  Widget _buildSearchResults() {
    if (_searchResults.isEmpty) {
      return const _EmptyState(
        message: 'Aucun résultat.\nEssayez le numéro du document ou une commune.',
      );
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              '${_searchResults.length} résultat${_searchResults.length > 1 ? 's' : ''}',
              style: const TextStyle(color: AppTheme.inkSoft, fontSize: 13),
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            itemCount: _searchResults.length,
            itemBuilder: (context, index) => ReportRow(
              report: _searchResults[index],
              onTap: () => _openReport(_searchResults[index]),
            ),
          ),
        ),
      ],
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Text(
          message,
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppTheme.inkSoft),
        ),
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