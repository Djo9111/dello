import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../models/claim.dart';

class ClaimsRepository {
  ClaimsRepository({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  Future<Claim> claimReport(
    String reportId, {
    String? message,
    String? answer,
  }) =>
      _single('/reports/$reportId/claims', {
        'message': ?message,
        'answer': ?answer,
      });

  Future<Claim> answerQuestion(String claimId, String answer) =>
      _single('/claims/$claimId/answer', {'answer': answer});

  Future<Claim> approve(String claimId) => _single('/claims/$claimId/approve', null);

  Future<Claim> reject(String claimId) => _single('/claims/$claimId/reject', null);

  Future<Claim> withdraw(String claimId) => _single('/claims/$claimId/withdraw', null);

  Future<List<Claim>> listMine() => _list('/claims/mine');

  Future<List<Claim>> listReceived() => _list('/claims/received');

  /// Appel explicite : le contact n'est jamais inclus dans les listes.
  Future<Contact> contact(String claimId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>('/claims/$claimId/contact');
      return Contact.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<Claim> _single(String path, Map<String, dynamic>? data) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(path, data: data ?? {});
      return Claim.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<List<Claim>> _list(String path) async {
    try {
      final response = await _dio.get<List<dynamic>>(path);
      return (response.data ?? [])
          .map((item) => Claim.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }
}