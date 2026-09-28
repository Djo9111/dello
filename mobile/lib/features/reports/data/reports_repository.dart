import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../models/report.dart';

class ReportsRepository {
  ReportsRepository({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

    Future<List<Report>> listPublic({
    ReportKind? kind,
    DocumentType? documentType,
    String? region,
    String? search,
    int limit = 20,
    int offset = 0,
  }) async {
    return _list('/reports', {
      'kind': ?kind?.value,
      'document_type': ?documentType?.value,
      'region': ?region,
      'search': ?search,
      'limit': limit,
      'offset': offset,
    });
  }

  Future<List<Report>> listMine({int limit = 20, int offset = 0}) =>
      _list('/reports/me', {'limit': limit, 'offset': offset});

  Future<List<Report>> matches(String reportId) =>
      _list('/reports/me/$reportId/matches', const {});

  Future<Report> getMine(String reportId) async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>('/reports/me/$reportId');
      return Report.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  /// Le numéro part vers l'API puis n'est plus conservé par l'application.
   /// Le numéro part vers l'API puis n'est plus conservé par l'application.
  Future<Report> create({
    required ReportKind kind,
    required DocumentType documentType,
    required String region,
    String? documentNumber,
    String? ownerName,
    String? commune,
    String? placeDetail,
    DateTime? occurredOn,
    double? latitude,
    double? longitude,
    String? verificationQuestion,
    String? verificationAnswer,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/reports',
        data: {
          'kind': kind.value,
          'document_type': documentType.value,
          'region': region,
          if (documentNumber != null && documentNumber.isNotEmpty)
            'document_number': documentNumber,
          if (ownerName != null && ownerName.isNotEmpty) 'owner_name': ownerName,
          if (commune != null && commune.isNotEmpty) 'commune': commune,
          if (placeDetail != null && placeDetail.isNotEmpty)
            'place_detail': placeDetail,
          if (occurredOn != null)
            'occurred_on': occurredOn.toIso8601String().split('T').first,
          'latitude': ?latitude,
          'longitude': ?longitude,
          if (verificationQuestion != null && verificationQuestion.isNotEmpty)
            'verification_question': verificationQuestion,
          if (verificationAnswer != null && verificationAnswer.isNotEmpty)
            'verification_answer': verificationAnswer,
        },
      );
      return Report.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<Report> update(
    String reportId, {
    String? commune,
    String? placeDetail,
    bool? isPublished,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        '/reports/$reportId',
        data: {
          'commune': ?commune,
          'place_detail': ?placeDetail,
          'is_published': ?isPublished,
        },
      );
      return Report.fromJson(response.data!);
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<void> remove(String reportId) async {
    try {
      await _dio.delete<void>('/reports/$reportId');
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<List<Report>> _list(String path, Map<String, dynamic> query) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        path,
        queryParameters: query.isEmpty ? null : query,
      );
      return (response.data ?? [])
          .map((item) => Report.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }
}