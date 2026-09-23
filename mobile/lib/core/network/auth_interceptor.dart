import 'package:dio/dio.dart';

import '../storage/token_storage.dart';

/// Ajoute l'access token, et rafraîchit la session quand il expire.
///
/// Point critique : un seul appel à /auth/refresh à la fois. Le backend
/// révoque toute la session si un refresh token déjà utilisé lui revient,
/// donc deux rafraîchissements en parallèle déconnecteraient l'utilisateur.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required TokenStorage storage,
    required Dio plainDio,
    required void Function() onSessionExpired,
  })  : _storage = storage,
        _plainDio = plainDio,
        _onSessionExpired = onSessionExpired;

  static const _retriedKey = 'dello_retried';
  static const _publicPaths = {'/auth/login', '/auth/register', '/auth/refresh'};

  final TokenStorage _storage;
  final Dio _plainDio; // Dio sans intercepteur, pour éviter toute récursion
  final void Function() _onSessionExpired;

  Future<bool>? _ongoingRefresh;

  bool _isPublic(String path) => _publicPaths.any(path.endsWith);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (!_isPublic(options.path)) {
      final accessToken = await _storage.readAccessToken();
      if (accessToken != null) {
        options.headers['Authorization'] = 'Bearer $accessToken';
      }
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final request = err.requestOptions;
    final isRetryable = err.response?.statusCode == 401 &&
        !_isPublic(request.path) &&
        request.extra[_retriedKey] != true;

    if (!isRetryable) {
      return handler.next(err);
    }

    final refreshed = await _refreshSession();

    if (!refreshed) {
      await _storage.clear();
      _onSessionExpired();
      return handler.next(err);
    }

    final accessToken = await _storage.readAccessToken();
    request.extra[_retriedKey] = true;
    request.headers['Authorization'] = 'Bearer $accessToken';

    try {
      final retried = await _plainDio.fetch<dynamic>(request);
      return handler.resolve(retried);
    } on DioException catch (error) {
      return handler.next(error);
    }
  }

  /// Un seul rafraîchissement à la fois : les appels concurrents
  /// attendent le même résultat au lieu d'en lancer un chacun.
  Future<bool> _refreshSession() {
    return _ongoingRefresh ??= _performRefresh().whenComplete(() {
      _ongoingRefresh = null;
    });
  }

  Future<bool> _performRefresh() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null) return false;

    try {
      final response = await _plainDio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );

      final data = response.data;
      if (data == null) return false;

      await _storage.saveTokens(
        accessToken: data['access_token'] as String,
        refreshToken: data['refresh_token'] as String,
      );
      return true;
    } on DioException {
      return false;
    }
  }
}