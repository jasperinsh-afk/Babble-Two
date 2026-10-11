import 'package:app_links/app_links.dart';
import 'package:go_router/go_router.dart';

import '../core/api/api_service.dart';
import '../core/storage/local_cache.dart';

/// OMEGA Deep Link 处理：冷启动 / 热启动
/// 支持 /nfc/{card_id} /vote/{id} /club/{id} /event/{id}
class DeepLinkHandler {
  DeepLinkHandler();

  final _appLinks = AppLinks();

  Future<void> init(GoRouter router) async {
    // 冷启动
    try {
      final initial = await _appLinks.getInitialLink();
      if (initial != null) await _handle(initial, router);
    } catch (_) {}

    // 热启动
    _appLinks.uriLinkStream.listen((uri) => _handle(uri, router));
  }

  Future<void> _handle(Uri uri, GoRouter router) async {
    final seg = uri.pathSegments;
    if (seg.length < 2) return;

    switch (seg[0]) {
      case 'nfc':
        await _handleNfc(seg[1], router);
        break;
      case 'vote':
        router.go('/vote/${seg[1]}');
        break;
      case 'club':
        router.go('/club/${seg[1]}');
        break;
      case 'event':
        router.go('/event/${seg[1]}');
        break;
    }
  }

  Future<void> _handleNfc(String cardId, GoRouter router) async {
    try {
      final card = await ApiService.nfcCard(cardId);
      await ApiService.nfcTap(cardId, true);
      router.go(card.route);
    } catch (_) {
      // 解析失败也要补报碰触（网络中断时暂存）
      await LocalCache.queueTap(cardId);
      router.go('/nfc');
    }
  }

  /// 联网后补报本地暂存的碰触事件
  static Future<void> syncPendingTaps() async {
    final pending = await LocalCache.pendingTaps();
    if (pending.isEmpty) return;
    for (final item in pending) {
      try {
        await ApiService.nfcTap(item['card_id'].toString(), true);
      } catch (_) {
        return; // 仍无网络，下次再试
      }
    }
    await LocalCache.clearPendingTaps();
  }

  /// 联网后补报本地暂存的投票
  static Future<void> syncPendingVotes() async {
    final pending = await LocalCache.pendingVotes();
    if (pending.isEmpty) return;
    for (final item in pending) {
      try {
        await ApiService.castVote(
          item['poll_id'] as int,
          (item['option_ids'] as List).map((e) => e as int).toList(),
        );
      } catch (_) {
        return;
      }
    }
    await LocalCache.clearPendingVotes();
  }
}
