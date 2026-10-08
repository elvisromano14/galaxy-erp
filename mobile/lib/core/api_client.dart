import 'package:dio/dio.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;
  String? _accessToken;
  String? _tenantSlug;

  ApiClient._internal() {
    dio = Dio(BaseOptions(
      baseUrl: 'http://localhost:8000',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        return handler.next(options);
      },
      onError: (DioException error, handler) {
        // Manejo centralizado RFC 9457
        return handler.next(error);
      },
    ));
  }

  void setSession({required String token, required String slug}) {
    _accessToken = token;
    _tenantSlug = slug;
  }

  void clearSession() {
    _accessToken = null;
    _tenantSlug = null;
  }

  String? get tenantSlug => _tenantSlug;
  bool get isAuthenticated => _accessToken != null;
}
