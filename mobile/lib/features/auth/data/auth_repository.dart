import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/storage/token_storage.dart';
import '../models/auth_user.dart';

class AuthRepository {
  AuthRepository({Dio? dio, TokenStorage? storage})
      : _dio = dio ?? ApiClient.instance.dio,
        _storage = storage ?? ApiClient.instance.tokenStorage;

  final Dio _dio;
  final TokenStorage _storage;

  /// Première étape : aucun compte n'est créé, un code part par SMS.
  /// La réponse est la même que le numéro soit libre ou déjà inscrit.
  Future<void> startRegistration({
    required String phoneNumber,
    required String fullName,
    required String password,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/auth/register',
        data: {
          'phone_number': phoneNumber,
          'full_name': fullName,
          'password': password,
        },
      );
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  /// Seconde étape : le compte est créé et l'utilisateur connecté.
  Future<void> verifyPhone({
    required String phoneNumber,
    required String code,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/verify',
        data: {'phone_number': phoneNumber, 'code': code},
      );
      await _saveTokens(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<void> resendCode(String phoneNumber) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/auth/resend-code',
        data: {'phone_number': phoneNumber},
      );
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
      await _saveTokens(response.data!);
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

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    await _storage.saveTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
    );
  }
}