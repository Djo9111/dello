import 'package:flutter/foundation.dart';

import '../../core/network/api_exception.dart';
import 'data/notifications_repository.dart';

/// Compteur de non-lus partagé par l'application.
///
/// Sans notification push, la seule façon de savoir qu'il y a du nouveau
/// est de demander au serveur : au démarrage, au retour au premier plan,
/// et après chaque action qui peut en produire.
class NotificationsController extends ChangeNotifier {
  NotificationsController._();

  static final NotificationsController instance = NotificationsController._();

  final NotificationsRepository _repository = NotificationsRepository();

  int unreadCount = 0;

  Future<void> refresh() async {
    try {
      final count = await _repository.unreadCount();
      if (count != unreadCount) {
        unreadCount = count;
        notifyListeners();
      }
    } on ApiException {
      // Un compteur indisponible ne doit pas perturber l'écran en cours
    }
  }

  void clear() {
    if (unreadCount == 0) return;
    unreadCount = 0;
    notifyListeners();
  }

  void decrement() {
    if (unreadCount == 0) return;
    unreadCount -= 1;
    notifyListeners();
  }
}