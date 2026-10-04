enum NotificationEvent {
  claimReceived('claim_received'),
  claimApproved('claim_approved'),
  claimRejected('claim_rejected'),
  matchFound('match_found'),
  unknown('unknown');

  const NotificationEvent(this.value);
  final String value;

  static NotificationEvent fromValue(String value) => NotificationEvent.values
      .firstWhere((event) => event.value == value,
          orElse: () => NotificationEvent.unknown);

  /// Une demande reçue concerne un signalement dont je suis le déclarant.
  /// Une décision concerne une demande que j'ai envoyée.
  bool get isAboutClaim =>
      this == claimReceived || this == claimApproved || this == claimRejected;

  bool get amIReportOwner => this == claimReceived;
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.event,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
    this.targetId,
  });

  final String id;
  final NotificationEvent event;
  final String title;
  final String body;
  final bool isRead;
  final DateTime createdAt;
  final String? targetId;

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      id: json['id'] as String,
      event: NotificationEvent.fromValue(json['event'] as String),
      title: json['title'] as String,
      body: json['body'] as String,
      isRead: json['is_read'] as bool? ?? false,
      createdAt: DateTime.parse(json['created_at'] as String),
      targetId: json['target_id'] as String?,
    );
  }
}