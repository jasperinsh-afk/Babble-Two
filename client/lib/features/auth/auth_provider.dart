import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_service.dart';
import '../../core/storage/secure_storage.dart';
import '../../shared/models.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState extends ChangeNotifier {
  AuthStatus status = AuthStatus.unknown;
  User? user;
  String? error;

  Future<void> bootstrap() async {
    final loggedIn = await SecureStorage.isLoggedIn;
    if (!loggedIn) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      user = await ApiService.me();
      status = AuthStatus.authenticated;
    } catch (_) {
      await SecureStorage.clear();
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> login(String studentId, String password) async {
    error = null;
    try {
      final data = await ApiService.login(studentId, password);
      await _persist(data);
      status = AuthStatus.authenticated;
      notifyListeners();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> register({
    required String studentId,
    required String email,
    required String password,
    required String nickname,
    required String emailCode,
    String? grade,
    String? dormitory,
  }) async {
    error = null;
    try {
      final data = await ApiService.register(
        studentId: studentId,
        email: email,
        password: password,
        nickname: nickname,
        emailCode: emailCode,
        grade: grade,
        dormitory: dormitory,
      );
      await _persist(data);
      status = AuthStatus.authenticated;
      notifyListeners();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> _persist(Map<String, dynamic> data) async {
    final token = data['token'] as Map<String, dynamic>?;
    if (token != null) {
      await SecureStorage.saveTokens(
        access: token['access_token'].toString(),
        refresh: token['refresh_token'].toString(),
      );
    }
    final u = data['user'];
    if (u is Map<String, dynamic>) {
      user = User.fromJson(u);
      await SecureStorage.saveProfile(
        id: user!.id.toString(),
        nickname: user!.nickname,
        studentId: user!.studentId,
      );
    }
  }

  Future<void> logout() async {
    await SecureStorage.clear();
    user = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}

final authStateProvider = ChangeNotifierProvider<AuthState>((ref) => AuthState());
