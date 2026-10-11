import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../storage/local_cache.dart';
import '../storage/secure_storage.dart';
import 'api_endpoints.dart';

/// 统一网络层：Token 注入 / 401 无感刷新 / 统一错误码 / 网络中断暂存
class ApiClient {
  ApiClient._();

  static final Dio dio = _build();

  static Dio _build() {
    final d = Dio(
      BaseOptions(
        baseUrl: ApiEndpoints.baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
        sendTimeout: const Duration(seconds: 10),
        contentType: Headers.jsonContentType,
        responseType: ResponseType.json,
      ),
    );

    d.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await SecureStorage.accessToken;
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (err, handler) async {
        // 401 无感刷新：仅对 access token 过期处理一次
        final status = err.response?.statusCode;
        final path = err.requestOptions.path;
        if (status == 401 &&
            path != ApiEndpoints.refresh &&
            path != ApiEndpoints.login) {
          final ok = await _refreshToken(d);
          if (ok) {
            final retry = await _retry(err.requestOptions, d);
            return handler.resolve(retry);
          }
          await SecureStorage.clear();
        }
        handler.next(err);
      },
    ));

    if (kDebugMode) {
      d.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: false,
        error: true,
      ));
    }
    return d;
  }

  static Future<bool> _refreshToken(Dio d) async {
    final refresh = await SecureStorage.refreshToken;
    if (refresh == null || refresh.isEmpty) return false;
    try {
      final resp = await d.post(
        ApiEndpoints.refresh,
        data: {'refresh_token': refresh},
        options: Options(headers: {'Authorization': null}),
      );
      final data = resp.data['data'] ?? {};
      final access = data['access_token'] as String?;
      final newRefresh = data['refresh_token'] as String?;
      if (access == null) return false;
      await SecureStorage.saveTokens(
        access: access,
        refresh: newRefresh ?? refresh,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<Response<dynamic>> _retry(RequestOptions o, Dio d) {
    return d.request(
      o.path,
      data: o.data,
      queryParameters: o.queryParameters,
      options: Options(method: o.method, headers: o.headers),
    );
  }

  // ── 统一响应解包：{code, message, data, timestamp} ──

  /// 返回 data 字段；业务失败抛 ApiException
  static Future<dynamic> get(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final r = await dio.get(path, queryParameters: query);
    return _unwrap(r.data);
  }

  static Future<dynamic> post(
    String path, {
    Object? data,
    Map<String, dynamic>? query,
  }) async {
    final r = await dio.post(path, data: data, queryParameters: query);
    return _unwrap(r.data);
  }

  static Future<dynamic> put(String path, {Object? data}) async {
    final r = await dio.put(path, data: data);
    return _unwrap(r.data);
  }

  static Future<dynamic> delete(String path, {Object? data}) async {
    final r = await dio.delete(path, data: data);
    return _unwrap(r.data);
  }

  static dynamic _unwrap(dynamic body) {
    if (body is Map<String, dynamic> && body.containsKey('code')) {
      final code = body['code'] as int? ?? 0;
      if (code == 0) return body['data'];
      throw ApiException(code, body['message']?.toString() ?? '请求失败');
    }
    return body;
  }

  /// 网络中断时把操作暂存本地，联网后由 syncPending() 补报
  static Future<bool> isOffline(DioException e) =>
      Future.value(e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout);

  static Future<void> queueOfflineVote(int pollId, List<int> optionIds) =>
      LocalCache.queueVote(pollId, optionIds);
}

class ApiException implements Exception {
  final int code;
  final String message;

  ApiException(this.code, this.message);

  @override
  String toString() => 'ApiException($code): $message';
}
