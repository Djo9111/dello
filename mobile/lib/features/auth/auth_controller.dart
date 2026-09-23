import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/network/api_client.dart';
import 'data/auth_repository.dart';
import 'models/auth_user.dart';

enum AuthStatus { checking, authenticated, unauthenticated }

/// État d'authentification partagé par toute l'application.
class AuthController extends ChangeNotifier {
  AuthController._() {
    _expirySubscription =
        ApiClient.instance.onSessionExpired.listen((_) => _handleSessionExpired());
  }

  static final AuthController instance = AuthController._();

  final AuthRepository _repository = AuthRepository();
  late final StreamSubscription<void> _expirySubscription;

  AuthStatus status = AuthStatus.checking;
  AuthUser? user;

  /// Au démarrage : on vérifie la session auprès du serveur, et pas
  /// seulement la présence d'un token local. Un compte supprimé ou
  /// déconnecté ailleurs doit être détecté tout de suite.
  Future<void> bootstrap() async {
    if (!await _repository.hasStoredSession()) {
      _setUnauthenticated();
      return;
    }

    try {
      user = await _repository.currentUser();
      status = AuthStatus.authenticated;
      notifyListeners();
    } catch (_) {
      await _repository.logout();
      _setUnauthenticated();
    }
  }

  Future<void> login({
    required String phoneNumber,
    required String password,
  }) async {
    await _repository.login(phoneNumber: phoneNumber, password: password);
    user = await _repository.currentUser();
    status = AuthStatus.authenticated;
    notifyListeners();
  }

  Future<void> register({
    required String phoneNumber,
    required String fullName,
    required String password,
  }) async {
    await _repository.register(
      phoneNumber: phoneNumber,
      fullName: fullName,
      password: password,
    );
    await login(phoneNumber: phoneNumber, password: password);
  }

  Future<void> logout() async {
    await _repository.logout();
    _setUnauthenticated();
  }

  void _handleSessionExpired() {
    if (status == AuthStatus.unauthenticated) return;
    _setUnauthenticated();
  }

  void _setUnauthenticated() {
    user = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  @override
  void dispose() {
    _expirySubscription.cancel();
    super.dispose();
  }
}