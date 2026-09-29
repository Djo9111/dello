import 'package:dio/dio.dart';

/// Erreur d'API traduite en message affichable.
/// Les écrans n'ont jamais à manipuler des DioException.
class ApiException implements Exception {
  ApiException({
    required this.message,
    this.statusCode,
    this.fieldErrors = const {},
    this.retryAfterSeconds,
  });

  final String message;
  final int? statusCode;
  final Map<String, String> fieldErrors;

  /// Délai indiqué par le serveur avant une nouvelle tentative (en-tête Retry-After)
  final int? retryAfterSeconds;

  bool get isUnauthorized => statusCode == 401;
  bool get isRateLimited => statusCode == 429;

  factory ApiException.from(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        return ApiException(message: 'Le serveur met trop de temps à répondre');
      case DioExceptionType.connectionError:
        return ApiException(message: 'Connexion impossible. Vérifiez votre réseau.');
      default:
        return ApiException._fromResponse(error.response);
    }
  }

  factory ApiException._fromResponse(Response<dynamic>? response) {
    final status = response?.statusCode;
    final data = response?.data;
    final detail = data is Map<String, dynamic> ? data['detail'] : null;
    final retryAfter = int.tryParse(
      response?.headers.value('retry-after') ?? '',
    );

    // Erreur simple : {"detail": "Numéro ou mot de passe incorrect"}
    if (detail is String) {
      return ApiException(
        message: detail,
        statusCode: status,
        retryAfterSeconds: retryAfter,
      );
    }

    // Erreur de validation : {"detail": [{"field": ..., "message": ...}]}
    if (detail is List) {
      final fieldErrors = <String, String>{};
      final messages = <String>[];

      for (final item in detail) {
        if (item is! Map) continue;
        final field = item['field']?.toString();
        final message = item['message']?.toString() ?? 'Valeur invalide';
        messages.add(message);
        if (field != null && field.isNotEmpty) {
          fieldErrors[field] = message;
        }
      }

      return ApiException(
        message: messages.isEmpty ? 'Données invalides' : messages.first,
        statusCode: status,
        fieldErrors: fieldErrors,
        retryAfterSeconds: retryAfter,
      );
    }

    return ApiException(
      message: 'Une erreur est survenue. Réessayez.',
      statusCode: status,
      retryAfterSeconds: retryAfter,
    );
  }

  @override
  String toString() => message;
}