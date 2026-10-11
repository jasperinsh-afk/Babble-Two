import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// 轻量本地缓存：网络中断时暂存投票/打卡，恢复后自动补报
/// （PRD 网络中断本地暂存 + OMEGA N-102 本地缓存补报）
class LocalCache {
  LocalCache._();

  static const _kPendingVotes = 'goqd_pending_votes';
  static const _kPendingTaps = 'goqd_pending_nfc_taps';

  static Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  // ── 待补报投票 ──

  static Future<void> queueVote(int pollId, List<int> optionIds) async {
    final p = await _prefs;
    final list = p.getStringList(_kPendingVotes) ?? [];
    list.add(jsonEncode({'poll_id': pollId, 'option_ids': optionIds}));
    await p.setStringList(_kPendingVotes, list);
  }

  static Future<List<Map<String, dynamic>>> pendingVotes() async {
    final p = await _prefs;
    final list = p.getStringList(_kPendingVotes) ?? [];
    return list
        .map((e) => jsonDecode(e) as Map<String, dynamic>)
        .toList(growable: false);
  }

  static Future<void> clearPendingVotes() async {
    final p = await _prefs;
    await p.remove(_kPendingVotes);
  }

  // ── 待补报 NFC 碰触 ──

  static Future<void> queueTap(String cardId) async {
    final p = await _prefs;
    final list = p.getStringList(_kPendingTaps) ?? [];
    list.add(jsonEncode({'card_id': cardId}));
    await p.setStringList(_kPendingTaps, list);
  }

  static Future<List<Map<String, dynamic>>> pendingTaps() async {
    final p = await _prefs;
    final list = p.getStringList(_kPendingTaps) ?? [];
    return list
        .map((e) => jsonDecode(e) as Map<String, dynamic>)
        .toList(growable: false);
  }

  static Future<void> clearPendingTaps() async {
    final p = await _prefs;
    await p.remove(_kPendingTaps);
  }
}
