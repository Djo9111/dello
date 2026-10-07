import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../../auth/auth_controller.dart';
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
  final _searchFocus = FocusNode();

  Timer? _debounce;
  Map<DocumentType, List<Report>> _byFamily = {};
  List<Report> _searchResults = [];

  /// La recherche n'apparaît qu'après avoir choisi "J'ai perdu" : un champ
  /// seul ne dit pas ce qu'il faut y mettre.
  bool _searchOpen = false;

  /// Terme réellement envoyé au serveur. Distinct du texte en cours de
  /// frappe : le message "aucun résultat" ne doit pas clignoter.
  String _search = '';
  bool _hasSearched = false;

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
    _searchFocus.dispose();
    super.dispose();
  }

  void _openSearch() {
    setState(() => _searchOpen = true);
    // Le champ n'existe qu'après la reconstruction : demander le focus
    // immédiatement n'aurait aucun effet.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _searchFocus.requestFocus();
    });
  }

  void _closeSearch() {
    _debounce?.cancel();
    _searchController.clear();
    _searchFocus.unfocus();
    setState(() {
      _searchOpen = false;
      _search = '';
      _hasSearched = false;
    });
    _load();
  }

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    setState(() => _hasSearched = false);

    _debounce = Timer(_searchDebounce, () {
      setState(() => _search = value.trim());
      _load();
    });
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (_isSearching) {
        final results = await _repository.listPublic(search: _search, limit: 50);
        if (mounted) {
          setState(() {
            _searchResults = results;
            _hasSearched = true;
          });
        }
      } else {
        final results = await Future.wait(
          DocumentType.values.map(
            (type) => _repository.listPublic(
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
      MaterialPageRoute(builder: (_) => ReportsFamilyScreen(documentType: type)),
    );
    if (changed == true) _load();
  }

  Future<void> _declare(ReportKind kind) async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ReportFormScreen(
          initialKind: kind,
          initialDocumentNumber: _search.isEmpty ? null : _search,
        ),
      ),
    );

    if (created == true && mounted) {
      _closeSearch();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Déclaration enregistrée')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final firstName =
        (AuthController.instance.user?.fullName ?? '').split(' ').first;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: _searchOpen
                ? _SearchBar(
                    key: const ValueKey('recherche'),
                    controller: _searchController,
                    focusNode: _searchFocus,
                    onChanged: _onSearchChanged,
                    onClose: _closeSearch,
                  )
                : _ActionHeader(
                    key: const ValueKey('actions'),
                    firstName: firstName,
                    onLost: _openSearch,
                    onFound: () => _declare(ReportKind.found),
                  ),
          ),
          ..._buildContent(),
        ],
      ),
    );
  }

  List<Widget> _buildContent() {
    if (_isLoading) {
      return const [
        Padding(
          padding: EdgeInsets.symmetric(vertical: 48),
          child: Center(child: CircularProgressIndicator()),
        ),
      ];
    }

    if (_error != null) {
      return [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 32),
          child: Column(
            children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Réessayer')),
            ],
          ),
        ),
      ];
    }

    if (_isSearching) return _buildSearchResults();

    if (_byFamily.isEmpty) {
      return const [
        Padding(
          padding: EdgeInsets.symmetric(vertical: 40, horizontal: 32),
          child: Text(
            'Aucun signalement pour le moment.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppTheme.inkSoft),
          ),
        ),
      ];
    }

    return [
      const Padding(
        padding: EdgeInsets.fromLTRB(16, 4, 16, 10),
        child: Text(
          'RÉCEMMENT SIGNALÉS',
          style: TextStyle(
            fontSize: 11,
            letterSpacing: 1,
            fontWeight: FontWeight.w700,
            color: AppTheme.inkSoft,
          ),
        ),
      ),
      ..._byFamily.keys.map((type) {
        final style = DocumentStyle.of(type);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 8, 8),
              child: Row(
                children: [
                  Icon(style.icon, size: 18, color: style.color),
                  const SizedBox(width: 8),
                  Text(
                    type.label,
                    style: const TextStyle(
                      fontSize: 16,
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
              child: FamilyCarousel(
                reports: _byFamily[type]!,
                onReportTap: _openReport,
              ),
            ),
            const SizedBox(height: 16),
          ],
        );
      }),
    ];
  }

  List<Widget> _buildSearchResults() {
    if (_searchResults.isEmpty) {
      if (!_hasSearched) return const [SizedBox.shrink()];
      return [_NoResult(onDeclare: _declare)];
    }

    return [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
        child: Text(
          _searchResults.length > 1
              ? '${_searchResults.length} signalements correspondent'
              : 'Un signalement correspond',
          style: const TextStyle(color: AppTheme.inkSoft, fontSize: 13),
        ),
      ),
      ..._searchResults.map(
        (report) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: ReportRow(report: report, onTap: () => _openReport(report)),
        ),
      ),
    ];
  }
}

class _ActionHeader extends StatelessWidget {
  const _ActionHeader({
    super.key,
    required this.firstName,
    required this.onLost,
    required this.onFound,
  });

  final String firstName;
  final VoidCallback onLost;
  final VoidCallback onFound;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            firstName.isEmpty ? 'Bonjour' : 'Bonjour $firstName',
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: AppTheme.ink,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _ActionCard(
                  icon: Icons.search,
                  label: "J'ai perdu\nun document",
                  color: AppTheme.primary,
                  onTap: onLost,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _ActionCard(
                  icon: Icons.place_outlined,
                  label: "J'ai trouvé\nun document",
                  color: AppTheme.success,
                  onTap: onFound,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SearchBar extends StatelessWidget {
  const _SearchBar({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.onChanged,
    required this.onClose,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final ValueChanged<String> onChanged;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 4, 16, 16),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: onClose,
          ),
          Expanded(
            child: TextField(
              controller: controller,
              focusNode: focusNode,
              onChanged: onChanged,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                hintText: 'Numéro du document, commune ou nom',
                prefixIcon: Icon(Icons.search, color: AppTheme.inkSoft),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: Colors.white, size: 22),
              const SizedBox(height: 26),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  height: 1.25,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NoResult extends StatelessWidget {
  const _NoResult({required this.onDeclare});

  final void Function(ReportKind) onDeclare;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
      child: Column(
        children: [
          const Icon(Icons.search_off, size: 44, color: AppTheme.inkSoft),
          const SizedBox(height: 14),
          const Text(
            'Aucun signalement ne correspond.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => onDeclare(ReportKind.lost),
              child: const Text("J'ai perdu ce document"),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => onDeclare(ReportKind.found),
              child: const Text("J'ai trouvé ce document"),
            ),
          ),
        ],
      ),
    );
  }
}