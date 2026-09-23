import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/storage/token_storage.dart';
import '../models/auth_user.dart';

/// Appels à l'API d'authentification. Traduit toute erreur réseau
/// en ApiException : les écrans ne voient jamais de DioException.
class AuthRepository {
  AuthRepository({Dio? dio, TokenStorage? storage})
      : _dio = dio ?? ApiClient.instance.dio,
        _storage = storage ?? ApiClient.instance.tokenStorage;

  final Dio _dio;
  final TokenStorage _storage;

  Future<AuthUser> register({
    required String phoneNumber,
    required String fullName,
    required String password,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/register',
        data: {
          'phone_number': phoneNumber,
          'full_name': fullName,
          'password': password,
        },
      );
      return AuthUser.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<void> login({
    required String phoneNumber,
    required String password,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'phone_number': phoneNumber, 'password': password},
      );

      final data = response.data!;
      await _storage.saveTokens(
        accessToken: data['access_token'] as String,
        refreshToken: data['refresh_token'] as String,
      );
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<AuthUser> currentUser() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/users/me');
      return AuthUser.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  /// Révoque la session côté serveur avant de vider le téléphone.
  /// Sans cet appel, le refresh token resterait valide 14 jours en base.
  Future<void> logout() async {
    final refreshToken = await _storage.readRefreshToken();

    if (refreshToken != null) {
      try {
        await _dio.post<void>(
          '/auth/logout',
          data: {'refresh_token': refreshToken},
        );
      } on DioException {
        // Serveur injoignable : on vide quand même le stockage local
      }
    }

    await _storage.clear();
  }

  Future<bool> hasStoredSession() => _storage.hasSession();
}