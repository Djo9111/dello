import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/report_tile.dart';
import 'report_public_detail_screen.dart';

/// Liste complète d'une famille, avec défilement infini.
class ReportsFamilyScreen extends StatefulWidget {
  const ReportsFamilyScreen({
    super.key,
    required this.documentType,
    this.kind,
  });

  final DocumentType documentType;
  final ReportKind? kind;

  @override
  State<ReportsFamilyScreen> createState() => _ReportsFamilyScreenState();
}

class _ReportsFamilyScreenState extends State<ReportsFamilyScreen> {
  static const _pageSize = 20;

  final _repository = ReportsRepository();
  final _scrollController = ScrollController();

  final List<Report> _reports = [];
  bool _isLoading = true;
  bool _isLoadingMore = false;
  bool _hasMore = true;
  bool _hasChanged = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadFirstPage();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final position = _scrollController.position;
    // Chargement anticipé : 400 pixels avant le bas, pour éviter que
    // l'utilisateur voie la liste s'arrêter.
    if (position.pixels >= position.maxScrollExtent - 400) _loadMore();
  }

  Future<void> _loadFirstPage() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _hasMore = true;
      _reports.clear();
    });

    try {
      final page = await _fetch(0);
      if (mounted) {
        setState(() {
          _reports.addAll(page);
          _hasMore = page.length == _pageSize;
        });
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_isLoadingMore || !_hasMore || _isLoading) return;

    setState(() => _isLoadingMore = true);

    try {
      final page = await _fetch(_reports.length);
      if (mounted) {
        setState(() {
          _reports.addAll(page);
          // Moins d'éléments que demandé : c'était la dernière page
          _hasMore = page.length == _pageSize;
        });
      }
    } on ApiException {
      if (mounted) setState(() => _hasMore = false);
    } finally {
      if (mounted) setState(() => _isLoadingMore = false);
    }
  }

  Future<List<Report>> _fetch(int offset) => _repository.listPublic(
        kind: widget.kind,
        documentType: widget.documentType,
        limit: _pageSize,
        offset: offset,
      );

  Future<void> _open(Report report) async {
    final claimed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => ReportPublicDetailScreen(report: report)),
    );
    if (claimed == true) {
      _hasChanged = true;
      _loadFirstPage();
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
        appBar: AppBar(title: Text(widget.documentType.label)),
        body: _buildBody(),
      ),
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
            FilledButton(onPressed: _loadFirstPage, child: const Text('Réessayer')),
          ],
        ),
      );
    }

    if (_reports.isEmpty) {
      return const Center(
        child: Text(
          'Aucun signalement dans cette catégorie.',
          style: TextStyle(color: AppTheme.inkSoft),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadFirstPage,
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
        itemCount: _reports.length + (_isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= _reports.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          final report = _reports[index];
          return ReportRow(report: report, onTap: () => _open(report));
        },
      ),
    );
  }
}