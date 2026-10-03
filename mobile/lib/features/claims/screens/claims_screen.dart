import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../data/claims_repository.dart';
import '../models/claim.dart';
import 'claim_detail_screen.dart';

class ClaimsScreen extends StatefulWidget {
  const ClaimsScreen({super.key});

  @override
  State<ClaimsScreen> createState() => _ClaimsScreenState();
}

class _ClaimsScreenState extends State<ClaimsScreen>
    with SingleTickerProviderStateMixin {
  final _repository = ClaimsRepository();
  late final TabController _tabController =
      TabController(length: 2, vsync: this);

  List<Claim> _mine = [];
  List<Claim> _received = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final mine = await _repository.listMine();
      final received = await _repository.listReceived();
      if (mounted) {
        setState(() {
          _mine = mine;
          _received = received;
        });
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _open(Claim claim, {required bool isReportOwner}) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ClaimDetailScreen(claim: claim, isReportOwner: isReportOwner),
      ),
    );
    if (changed == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Mes demandes'),
            Tab(text: 'Reçues'),
          ],
        ),
        Expanded(
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(_error!),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed: _load,
                            child: const Text('Réessayer'),
                          ),
                        ],
                      ),
                    )
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _ClaimList(
                          claims: _mine,
                          emptyLabel: 'Vous n\'avez envoyé aucune demande.',
                          onTap: (claim) => _open(claim, isReportOwner: false),
                          onRefresh: _load,
                        ),
                        _ClaimList(
                          claims: _received,
                          emptyLabel: 'Aucune demande sur vos signalements.',
                          onTap: (claim) => _open(claim, isReportOwner: true),
                          onRefresh: _load,
                        ),
                      ],
                    ),
        ),
      ],
    );
  }
}

class _ClaimList extends StatelessWidget {
  const _ClaimList({
    required this.claims,
    required this.emptyLabel,
    required this.onTap,
    required this.onRefresh,
  });

  final List<Claim> claims;
  final String emptyLabel;
  final void Function(Claim) onTap;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    if (claims.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(emptyLabel, textAlign: TextAlign.center),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: claims.length,
        itemBuilder: (context, index) {
          final claim = claims[index];
          return Card(
            elevation: 0,
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
            ),
            child: ListTile(
              onTap: () => onTap(claim),
              title: Text(claim.report.documentsLabel),
              subtitle: Text(
                '${claim.report.locationLabel} · ${claim.status.label}',
              ),
              trailing: claim.isVerified
                  ? const Icon(Icons.check_circle, color: Colors.green)
                  : const Icon(Icons.chevron_right),
            ),
          );
        },
      ),
    );
  }
}