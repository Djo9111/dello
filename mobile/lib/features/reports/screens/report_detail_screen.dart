import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../data/reports_repository.dart';
import '../models/report.dart';
import '../widgets/report_tile.dart';
import '../widgets/documents_section.dart';

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
  bool _isSharing = false;
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
      final matches = report.hasAnyDocumentNumber
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

  /// Le texte vient du serveur : l'application ne le compose pas, donc
  /// elle ne peut pas y ajouter un numéro de téléphone par erreur.
  Future<void> _share() async {
    if (_isSharing) return;
    setState(() => _isSharing = true);

    try {
      final content = await _repository.shareContent(widget.reportId);
      await SharePlus.instance.share(
        ShareParams(text: content.text, subject: 'Signalement Dello'),
      );
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _isSharing = false);
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

  Future<void> _confirmClose() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Document restitué ?'),
        content: const Text(
          'Le signalement sortira de la liste et les demandes en attente '
          'seront refusées.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Confirmer'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await _repository.close(widget.reportId);
      _hasChanged = true;
      await _load();
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
              tooltip: 'Partager',
              icon: _isSharing
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.share_outlined),
              onPressed: _isLoading ? null : _share,
            ),
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
    final isClosed = report.status == ReportStatus.closed;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
                Text(
          report.documentsLabel,
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text('${report.kindLabel} · ${report.status.label}'),
        const SizedBox(height: 20),
        _ShareBanner(onShare: _isSharing ? null : _share),
        const SizedBox(height: 24),
        DocumentsSection(report: report),
        const SizedBox(height: 8),
        _InfoRow(label: 'Lieu précis', value: report.placeDetail ?? 'Non renseigné'),
        const Divider(height: 32),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Visible par les autres utilisateurs'),
          value: report.isPublished ?? true,
          onChanged: isClosed ? null : _togglePublication,
        ),
        const Divider(height: 32),
        Text('Correspondances', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 4),
        Text(
          report.hasAnyDocumentNumber
              ? 'Signalements portant au moins un document en commun.'
              : 'Ajoutez le numéro d\'un document pour activer le rapprochement automatique.',
          style: const TextStyle(color: AppTheme.inkSoft, fontSize: 13),
        ),
        const SizedBox(height: 12),
        if (_matches.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('Aucune correspondance pour le moment.'),
          )
        else
          ..._matches.map((match) => ReportRow(report: match)),
        const Divider(height: 32),
        if (!isClosed)
          OutlinedButton.icon(
            onPressed: _confirmClose,
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Document restitué'),
          ),
      ],
    );
  }
}

class _ShareBanner extends StatelessWidget {
  const _ShareBanner({this.onShare});

  final VoidCallback? onShare;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.accentSoft,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.campaign_outlined, color: AppTheme.accent),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Faites circuler sans donner votre numéro',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Le lien partagé affiche les informations masquées. '
            'Celui qui a votre document passe par Dello pour vous joindre.',
            style: TextStyle(fontSize: 13, color: AppTheme.inkSoft),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: onShare,
            icon: const Icon(Icons.share_outlined, size: 18),
            label: const Text('Partager'),
            style: FilledButton.styleFrom(
              backgroundColor: AppTheme.accent,
              minimumSize: const Size.fromHeight(46),
            ),
          ),
        ],
      ),
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
            child: Text(label, style: const TextStyle(color: AppTheme.inkSoft)),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}