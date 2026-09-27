/// Configuration de l'application, injectée au moment du build.
///
/// Par défaut : l'émulateur Android, qui voit le PC sur 10.0.2.2.
/// Sur téléphone physique, passer l'adresse du PC au lancement :
///   flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000/api/v1
///
/// En release :
///   flutter build apk --dart-define=API_BASE_URL=https://api.dello.sn/api/v1
class AppConfig {
  const AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 15);

  /// Vrai uniquement pour un build de release.
  static const bool isRelease = bool.fromEnvironment('dart.vm.product');
}