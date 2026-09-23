import 'package:dello/core/network/api_exception.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

DioException _httpError(int statusCode, dynamic body) {
  final options = RequestOptions(path: '/auth/login');
  return DioException(
    requestOptions: options,
    type: DioExceptionType.badResponse,
    response: Response<dynamic>(
      requestOptions: options,
      statusCode: statusCode,
      data: body,
    ),
  );
}

void main() {
  test('message simple du backend', () {
    final exception = ApiException.from(
      _httpError(401, {'detail': 'Numéro ou mot de passe incorrect'}),
    );

    expect(exception.message, 'Numéro ou mot de passe incorrect');
    expect(exception.isUnauthorized, isTrue);
  });

  test('erreurs de validation rangées par champ', () {
    final exception = ApiException.from(
      _httpError(422, {
        'detail': [
          {'field': 'phone_number', 'message': 'Numéro de mobile sénégalais invalide'},
          {'field': 'password', 'message': 'Ce mot de passe est trop courant'},
        ],
      }),
    );

    expect(exception.fieldErrors['phone_number'], 'Numéro de mobile sénégalais invalide');
    expect(exception.fieldErrors['password'], 'Ce mot de passe est trop courant');
    expect(exception.message, 'Numéro de mobile sénégalais invalide');
  });

  test('erreur de validation sans champ associé', () {
    final exception = ApiException.from(
      _httpError(422, {
        'detail': [
          {'field': null, 'message': 'Le mot de passe ne doit pas contenir votre numéro'},
        ],
      }),
    );

    expect(exception.message, 'Le mot de passe ne doit pas contenir votre numéro');
    expect(exception.fieldErrors, isEmpty);
  });

  test('trop de tentatives', () {
    final exception = ApiException.from(
      _httpError(429, {'detail': 'Trop de tentatives. Réessayez dans une minute.'}),
    );

    expect(exception.isRateLimited, isTrue);
  });

  test('réseau indisponible', () {
    final exception = ApiException.from(
      DioException(
        requestOptions: RequestOptions(path: '/health'),
        type: DioExceptionType.connectionError,
      ),
    );

    expect(exception.message, contains('Connexion impossible'));
    expect(exception.statusCode, isNull);
  });

  test('réponse inattendue du serveur', () {
    final exception = ApiException.from(_httpError(500, {'detail': 'Erreur interne'}));

    expect(exception.message, 'Erreur interne');
    expect(exception.statusCode, 500);
  });
}