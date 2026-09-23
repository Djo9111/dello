import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../config/app_config.dart';
import '../storage/token_storage.dart';
import 'auth_interceptor.dart';

/// Point d'entrée réseau unique de l'application.
/// Une seule instance, sinon la protection contre les rafraîchissements
/// concurrents ne sert plus à rien.
class ApiClient {
  ApiClient._() {
    final options = BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: AppConfig.connectTimeout,
      receiveTimeout: AppConfig.receiveTimeout,
      contentType: 'application/json',
    );

    _plainDio = Dio(options);
    dio = Dio(options);

    dio.interceptors.add(
      AuthInterceptor(
        storage: tokenStorage,
        plainDio: _plainDio,
        onSessionExpired: () => _sessionExpired.add(null),
      ),
    );

    if (!AppConfig.isRelease) {
      dio.interceptors.add(_SafeLogInterceptor());
    }
  }

  static final ApiClient instance = ApiClient._();

  final TokenStorage tokenStorage = TokenStorage();
  final StreamController<void> _sessionExpired =
      StreamController<void>.broadcast();

  late final Dio dio;
  late final Dio _plainDio;

  /// Émis quand la session est définitivement perdue (refresh refusé).
  /// L'app écoute ce flux pour revenir à l'écran de connexion.
  Stream<void> get onSessionExpired => _sessionExpired.stream;
}

/// Journalisation volontairement minimale : ni en-têtes, ni corps.
/// Un token ne doit jamais apparaître dans logcat.
class _SafeLogInterceptor extends Interceptor {
  @override
  void onResponse(Response<dynamic> response, ResponseInterceptorHandler handler) {
    debugPrint(
      '${response.requestOptions.method} ${response.requestOptions.path} '
      '-> ${response.statusCode}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    debugPrint(
      '${err.requestOptions.method} ${err.requestOptions.path} '
      '-> ${err.response?.statusCode ?? err.type.name}',
    );
    handler.next(err);
  }
}