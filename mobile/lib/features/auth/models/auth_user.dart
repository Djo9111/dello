/// Utilisateur tel que renvoyé par GET /users/me.
class AuthUser {
  const AuthUser({
    required this.id,
    required this.phoneNumber,
    required this.fullName,
    required this.isPhoneVerified,
  });

  final String id;
  final String phoneNumber;
  final String fullName;
  final bool isPhoneVerified;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as String,
      phoneNumber: json['phone_number'] as String,
      fullName: json['full_name'] as String,
      isPhoneVerified: json['is_phone_verified'] as bool? ?? false,
    );
  }
}