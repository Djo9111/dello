import 'package:flutter/material.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_theme.dart';
import '../../claims/data/claims_repository.dart';
import '../../claims/screens/claim_detail_screen.dart';
import '../../reports/data/reports_repository.dart';
import '../../reports/screens/report_public_detail_screen.dart';
import '../data/notifications_repository.dart';
import '../models/app_notification.dart';
import '../notifications_controller.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final _repository = NotificationsRepository();
  final _claims = ClaimsRepository();
  final _reports = ReportsRepository();

  List<AppNotification> _notifications = [];
  bool _isLoading = true;
  bool _isOpening = false;
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
      final notifications = await _repository.list();
      if (mounted) setState(() => _notifications = notifications);
      await NotificationsController.instance.refresh();
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _markAllAsRead() async {
    try {
      await _repository.markAllAsRead();
      NotificationsController.instance.clear();
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  /// Ouvre l'objet concerné : une demande pour les trois événements de
  /// revendication, un signalement pour une correspondance.
  Future<void> _open(AppNotification notification) async {
    if (_isOpening || notification.targetId == null) return;
    setState(() => _isOpening = true);

    try {
      if (!notification.isRead) {
        await _repository.markAsRead(notification.id);
        NotificationsController.instance.decrement();
      }

      if (notification.event.isAboutClaim) {
        final claim = await _claims.getClaim(notification.targetId!);
        if (!mounted) return;
        await Navigator.of(context).push<bool>(
          MaterialPageRoute(
            builder: (_) => ClaimDetailScreen(
              claim: claim,
              isReportOwner: notification.event.amIReportOwner,
            ),
          ),
        );
      } else {
        final report = await _reports.getPublic(notification.targetId!);
        if (!mounted) return;
        await Navigator.of(context).push<bool>(
          MaterialPageRoute(
            builder: (_) => ReportPublicDetailScreen(report: report),
          ),
        );
      }

      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _isOpening = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (_notifications.any((notification) => !notification.isRead))
            TextButton(
              onPressed: _markAllAsRead,
              child: const Text('Tout marquer comme lu'),
            ),
        ],
      ),
      body: _buildBody(),
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

    if (_notifications.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Text(
            'Aucune notification pour le moment.\nVous serez prévenu dès qu\'un '
            'document correspondant au vôtre sera signalé.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppTheme.inkSoft),
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _notifications.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, index) =>
            _NotificationTile(
          notification: _notifications[index],
          onTap: () => _open(_notifications[index]),
        ),
      ),
    );
  }
}

class _NotificationTile extends StatelessWidget {
  const _NotificationTile({required this.notification, required this.onTap});

  final AppNotification notification;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isUnread = !notification.isRead;
    final color = switch (notification.event) {
      NotificationEvent.matchFound => AppTheme.success,
      NotificationEvent.claimRejected => Theme.of(context).colorScheme.error,
      _ => AppTheme.primary,
    };

    final icon = switch (notification.event) {
      NotificationEvent.matchFound => Icons.find_in_page_outlined,
      NotificationEvent.claimReceived => Icons.handshake_outlined,
      NotificationEvent.claimApproved => Icons.check_circle_outline,
      NotificationEvent.claimRejected => Icons.cancel_outlined,
      _ => Icons.notifications_outlined,
    };

    return Card(
      // Une notification non lue se repère d'un coup d'oeil
      color: isUnread ? AppTheme.accentSoft : Colors.white,
      child: ListTile(
        onTap: onTap,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(
          notification.title,
          style: TextStyle(
            fontWeight: isUnread ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            notification.body,
            style: const TextStyle(fontSize: 13, color: AppTheme.inkSoft),
          ),
        ),
        trailing: notification.targetId == null
            ? null
            : const Icon(Icons.chevron_right),
      ),
    );
  }
}