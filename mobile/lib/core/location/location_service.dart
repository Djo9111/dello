import 'package:geolocator/geolocator.dart';

/// Position courante, utilisée uniquement pour un document trouvé :
/// le déclarant est alors sur place, donc la position a du sens.
class LocationService {
  const LocationService._();

  static Future<Position?> currentPosition() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const LocationFailure('Activez la localisation sur votre téléphone');
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied) {
      throw const LocationFailure('Position refusée');
    }
    if (permission == LocationPermission.deniedForever) {
      throw const LocationFailure(
        'Position bloquée. Autorisez-la dans les paramètres du téléphone.',
      );
    }

    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 20),
      ),
    );
  }
}

class LocationFailure implements Exception {
  const LocationFailure(this.message);

  final String message;

  @override
  String toString() => message;
}