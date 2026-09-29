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
    await _loadCurrentUser();
  }

  /// Demande d'un code. Le compte n'existe pas encore à ce stade.
  Future<void> startRegistration({
    required String phoneNumber,
    required String fullName,
    required String password,
  }) {
    return _repository.startRegistration(
      phoneNumber: phoneNumber,
      fullName: fullName,
      password: password,
    );
  }

  Future<void> resendCode(String phoneNumber) =>
      _repository.resendCode(phoneNumber);

  /// Vérification du code : le compte est créé côté serveur et
  /// l'utilisateur se retrouve connecté.
  Future<void> verifyPhone({
    required String phoneNumber,
    required String code,
  }) async {
    await _repository.verifyPhone(phoneNumber: phoneNumber, code: code);
    await _loadCurrentUser();
  }

  Future<void> logout() async {
    await _repository.logout();
    _setUnauthenticated();
  }

  Future<void> _loadCurrentUser() async {
    user = await _repository.currentUser();
    status = AuthStatus.authenticated;
    notifyListeners();
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