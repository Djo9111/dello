import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/document_style.dart';
import '../widgets/family_carousel.dart';
import '../widgets/report_tile.dart';
import 'report_form_screen.dart';
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
  static const _minSearchLength = 2;

  final _repository = ReportsRepository();
  final _searchController = TextEditingController();

  Timer? _debounce;
  Map<DocumentType, List<Report>> _byFamily = {};
  List<Report> _searchResults = [];

  /// Terme réellement envoyé au serveur. Distinct du texte en cours de
  /// frappe : le message "aucun résultat" ne doit pas clignoter à chaque
  /// lettre tapée.
  String _search = '';
  bool _hasSearched = false;

  ReportKind? _kind;
  bool _isLoading = true;
  String? _error;

  bool get _isSearching => _search.length >= _minSearchLength;

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

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    setState(() => _hasSearched = false);

    _debounce = Timer(_searchDebounce, () {
      setState(() => _search = value.trim());
      _load();
    });
  }

  void _clearSearch() {
    _debounce?.cancel();
    _searchController.clear();
    setState(() {
      _search = '';
      _hasSearched = false;
    });
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
        if (mounted) {
          setState(() {
            _searchResults = results;
            _hasSearched = true;
          });
        }
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

  /// Le numéro tapé part dans le formulaire : l'utilisateur l'a déjà saisi,
  /// le redemander serait une friction inutile.
  Future<void> _declare(ReportKind kind) async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ReportFormScreen(
          initialKind: kind,
          initialDocumentNumber: _search,
        ),
      ),
    );

    if (created == true && mounted) {
      _clearSearch();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Déclaration enregistrée')),
      );
    }
  }

  void _setKind(ReportKind? kind) {
    setState(() => _kind = kind);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _SearchHeader(
          controller: _searchController,
          onChanged: _onSearchChanged,
          onClear: _clearSearch,
          isSearching: _isSearching,
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
      // Tant que la recherche n'a pas abouti, on n'affiche rien : le
      // message ne doit pas apparaître pendant la frappe.
      if (!_hasSearched) return const SizedBox.shrink();
      return _NoResult(onDeclare: _declare);
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              _searchResults.length > 1
                  ? '${_searchResults.length} signalements correspondent'
                  : 'Un signalement correspond',
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

class _SearchHeader extends StatelessWidget {
  const _SearchHeader({
    required this.controller,
    required this.onChanged,
    required this.onClear,
    required this.isSearching,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;
  final bool isSearching;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // L'accroche disparaît pendant la recherche, pour laisser la
          // place aux résultats sur les petits écrans.
          if (!isSearching) ...[
            const Text(
              'Vous avez perdu un document ?',
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w700,
                color: AppTheme.ink,
              ),
            ),
            const SizedBox(height: 2),
            const Text(
              "Entrez son numéro pour voir s'il a été signalé.",
              style: TextStyle(fontSize: 13, color: AppTheme.inkSoft),
            ),
            const SizedBox(height: 12),
          ],
          TextField(
            controller: controller,
            onChanged: onChanged,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Numéro du document, commune ou nom',
              prefixIcon: const Icon(Icons.search, color: AppTheme.inkSoft),
              suffixIcon: controller.text.isEmpty
                  ? null
                  : IconButton(icon: const Icon(Icons.close), onPressed: onClear),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
          ),
        ],
      ),
    );
  }
}

class _NoResult extends StatelessWidget {
  const _NoResult({required this.onDeclare});

  final void Function(ReportKind) onDeclare;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 24),
      children: [
        const Icon(Icons.search_off, size: 48, color: AppTheme.inkSoft),
        const SizedBox(height: 16),
        const Text(
          'Aucun signalement ne correspond pour le moment.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        const Text(
          'Déclarez votre document : vous serez prévenu dès que quelqu\'un '
          'le signalera.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 13, color: AppTheme.inkSoft),
        ),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: () => onDeclare(ReportKind.lost),
          icon: const Icon(Icons.search_off_outlined, size: 18),
          label: const Text("J'ai perdu ce document"),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () => onDeclare(ReportKind.found),
          icon: const Icon(Icons.inventory_2_outlined, size: 18),
          label: const Text("J'ai trouvé ce document"),
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