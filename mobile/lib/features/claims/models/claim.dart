import '../../reports/models/report.dart';

enum ClaimStatus {
  pending('pending', 'En attente'),
  verified('verified', 'Acceptée'),
  rejected('rejected', 'Refusée'),
  withdrawn('withdrawn', 'Annulée');

  const ClaimStatus(this.value, this.label);
  final String value;
  final String label;

  static ClaimStatus fromValue(String value) => ClaimStatus.values
      .firstWhere((status) => status.value == value, orElse: () => ClaimStatus.pending);
}

class Claim {
  const Claim({
    required this.id,
    required this.status,
    required this.answerAttempts,
    required this.createdAt,
    required this.report,
    this.message,
    this.resolvedAt,
  });

  final String id;
  final ClaimStatus status;
  final int answerAttempts;
  final DateTime createdAt;
  final Report report;
  final String? message;
  final DateTime? resolvedAt;

  bool get isPending => status == ClaimStatus.pending;
  bool get isVerified => status == ClaimStatus.verified;

  factory Claim.fromJson(Map<String, dynamic> json) {
    return Claim(
      id: json['id'] as String,
      status: ClaimStatus.fromValue(json['status'] as String),
      answerAttempts: json['answer_attempts'] as int? ?? 0,
      createdAt: DateTime.parse(json['created_at'] as String),
      report: Report.fromJson(json['report'] as Map<String, dynamic>),
      message: json['message'] as String?,
      resolvedAt: json['resolved_at'] == null
          ? null
          : DateTime.parse(json['resolved_at'] as String),
    );
  }
}

/// Coordonnées de l'autre partie, obtenues seulement sur une demande acceptée.
class Contact {
  const Contact({required this.fullName, required this.phoneNumber});

  final String fullName;
  final String phoneNumber;

  factory Contact.fromJson(Map<String, dynamic> json) => Contact(
        fullName: json['full_name'] as String,
        phoneNumber: json['phone_number'] as String,
      );
}