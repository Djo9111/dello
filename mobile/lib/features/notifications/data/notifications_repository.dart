import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../models/app_notification.dart';

class NotificationsRepository {
  NotificationsRepository({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  Future<List<AppNotification>> list({int limit = 30, int offset = 0}) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/notifications',
        queryParameters: {'limit': limit, 'offset': offset},
      );
      return (response.data ?? [])
          .map((item) => AppNotification.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<int> unreadCount() async {
    try {
      final response =
          await _dio.get<Map<String, dynamic>>('/notifications/unread-count');
      return response.data?['unread'] as int? ?? 0;
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<void> markAsRead(String notificationId) async {
    try {
      await _dio.post<void>('/notifications/$notificationId/read');
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }

  Future<void> markAllAsRead() async {
    try {
      await _dio.post<void>('/notifications/read-all');
    } on DioException catch (error) {
      throw ApiException.from(error);
    }
  }
}