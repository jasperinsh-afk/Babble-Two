import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Token 安全存储（flutter_secure_storage：iOS Keychain / Android Keystore）
class SecureStorage {
  SecureStorage._();

  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static const _kAccessToken = 'goqd_access_token';
  static const _kRefreshToken = 'goqd_refresh_token';
  static const _kUserId = 'goqd_user_id';
  static const _kNickname = 'goqd_nickname';
  static const _kStudentId = 'goqd_student_id';

  static Future<String?> get accessToken => _storage.read(key: _kAccessToken);
  static Future<String?> get refreshToken => _storage.read(key: _kRefreshToken);
  static Future<String?> get userId => _storage.read(key: _kUserId);
  static Future<String?> get nickname => _storage.read(key: _kNickname);
  static Future<String?> get studentId => _storage.read(key: _kStudentId);

  static Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await _storage.write(key: _kAccessToken, value: access);
    await _storage.write(key: _kRefreshToken, value: refresh);
  }

  static Future<void> saveProfile({
    required String id,
    required String nickname,
    String? studentId,
  }) async {
    await _storage.write(key: _kUserId, value: id);
    await _storage.write(key: _kNickname, value: nickname);
    if (studentId != null) {
      await _storage.write(key: _kStudentId, value: studentId);
    }
  }

  static Future<bool> get isLoggedIn async {
    final t = await accessToken;
    return t != null && t.isNotEmpty;
  }

  static Future<void> clear() => _storage.deleteAll();
}
