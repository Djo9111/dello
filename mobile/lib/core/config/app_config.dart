/// Configuration de l'application, injectée au moment du build.
///
/// En développement, la valeur par défaut pointe vers l'API locale :
/// 10.0.2.2 est l'adresse par laquelle l'émulateur Android voit ton PC.
///
/// En release, l'URL est passée au build :
///   flutter build apk --dart-define=API_BASE_URL=https://api.dello.sn/api/v1
class AppConfig {
  const AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.1.26:8000/api/v1',
  );

  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 15);

  /// Vrai uniquement pour un build de release.
  static const bool isRelease = bool.fromEnvironment('dart.vm.product');
}