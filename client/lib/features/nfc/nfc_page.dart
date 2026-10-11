import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:nfc_manager/nfc_manager.dart';

import '../../app/theme.dart';
import '../../core/api/api_service.dart';
import '../../core/storage/local_cache.dart';
import '../../shared/models.dart';
import '../../shared/widgets.dart';

/// OMEGA：碰一碰校园海报
/// OMEGA 文档 §5 NFC 读取 / §6 未安装 App 时跳转
class NfcPage extends StatefulWidget {
  const NfcPage({super.key});

  @override
  State<NfcPage> createState() => _NfcPageState();
}

class _NfcPageState extends State<NfcPage> {
  NfcCheckin? _checkin;
  bool _scanning = false;
  String? _message;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await ApiService.nfcCheckins();
      setState(() => _checkin = c);
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _startScan() async {
    final available = await NfcManager.instance.isAvailable();
    if (!available) {
      setState(() => _message = '本设备不支持 NFC，或 NFC 未开启');
      return;
    }
    setState(() {
      _scanning = true;
      _message = '请将手机靠近海报上的 NFC 标签…';
    });

    try {
      await NfcManager.instance.startSession(
        pollingOptions: {
          NfcPollingOption.iso14443,
          NfcPollingOption.iso15693,
          NfcPollingOption.iso18092,
        },
        onDiscovered: (NfcTag tag) async {
          final cardId = _extractCardId(tag);
          await NfcManager.instance.stopSession();
          if (cardId == null) {
            if (mounted) setState(() {
              _scanning = false;
              _message = '不支持的标签格式';
            });
            return;
          }
          await _handleCard(cardId);
        },
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _scanning = false;
          _message = '读取失败：$e';
        });
      }
    }
  }

  /// 从 NDEF 记录中提取 card_id（写入格式：https://goqd.com/nfc/{card_id}）
  String? _extractCardId(NfcTag tag) {
    final raw = tag.data;
    if (raw is! Map) return null;
    final ndef = raw['ndef'];
    if (ndef is! Map) return null;
    final cached = ndef['cachedMessage'];
    if (cached is! Map) return null;
    final records = cached['records'];
    if (records is! List) return null;

    for (final r in records) {
      if (r is! Map) continue;
      final payload = r['payload'];
      if (payload is! List || payload.isEmpty) continue;
      // 第 1 字节为 URI 标识，其后为 URI 明文
      final bytes = payload.skip(1).whereType<int>().toList();
      final uri = String.fromCharCodes(bytes);
      final seg = uri.split('/nfc/');
      if (seg.length > 1 && seg.last.isNotEmpty) return seg.last.trim();
      // 兼容纯 card_id 写入
      if (RegExp(r'^[A-Z]{2}-[A-Z]{2}-\d{2}-[A-Z0-9]+$').hasMatch(uri.trim())) {
        return uri.trim();
      }
    }
    return null;
  }

  Future<void> _handleCard(String cardId) async {
    setState(() {
      _scanning = false;
      _message = '识别到卡片：$cardId';
    });
    try {
      final card = await ApiService.nfcCard(cardId);
      await ApiService.nfcTap(cardId, true);
      await _load();
      if (!mounted) return;
      switch (card.targetType) {
        case NfcTargetType.vote:
          context.go('/vote/${card.targetId}');
          break;
        case NfcTargetType.club:
          context.go('/club/${card.targetId}');
          break;
        case NfcTargetType.event:
          context.go('/calendar');
          break;
        case NfcTargetType.download:
          setState(() => _message = '该卡片指向下载页');
          break;
      }
    } catch (_) {
      // 网络失败：本地暂存，联网后补报（OMEGA N-102）
      await LocalCache.queueTap(cardId);
      if (mounted) setState(() => _message = '网络不可用，打卡已暂存，联网后自动补报');
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _checkin;
    return Scaffold(
      appBar: AppBar(title: const Text('碰一碰')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              gradient: const LinearGradient(
                colors: [GoQDColors.primary, GoQDColors.primaryLight],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Column(
              children: [
                Icon(
                  _scanning ? Icons.nfc : Icons.nfc_outlined,
                  size: 72,
                  color: Colors.white,
                ),
                const SizedBox(height: 14),
                const Text('把手机靠近校园海报上的贴纸',
                    style: TextStyle(color: Colors.white, fontSize: 15)),
                const SizedBox(height: 4),
                const Text('不用扫码，碰一下就打开',
                    style: TextStyle(color: Colors.white70, fontSize: 13)),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _scanning ? null : _startScan,
                    icon: const Icon(Icons.touch_app, size: 18),
                    label: Text(_scanning ? '扫描中…' : '开始碰一碰'),
                    style: FilledButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: GoQDColors.primary,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_message != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: GoQDColors.border),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, size: 18, color: GoQDColors.primary),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_message!)),
                ],
              ),
            ),
          ],
          const SizedBox(height: 24),
          const Text('我的打卡进度',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          if (_error != null)
            ErrorView(message: _error!, onRetry: _load)
          else if (c == null)
            const LoadingView()
          else
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: GoQDColors.border),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _StatBox(label: '已打卡卡片', value: '${c.uniqueCards}'),
                      _StatBox(label: '累计碰触', value: '${c.totalTaps}'),
                      _StatBox(label: '解锁勋章', value: _badgeText(c.uniqueCards)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: (c.uniqueCards / 5).clamp(0.0, 1.0),
                      minHeight: 8,
                      backgroundColor: GoQDColors.border,
                      valueColor: const AlwaysStoppedAnimation(GoQDColors.accent),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text('碰触 5 个不同卡片解锁「NFC 探索者」勋章',
                      style: TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
                  if (c.cards.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    const Divider(),
                    for (final card in c.cards)
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.nfc, size: 18, color: GoQDColors.primary),
                        title: Text(card.cardId, style: const TextStyle(fontSize: 13)),
                        trailing: Text('${card.tapCount} 次',
                            style: const TextStyle(
                                fontSize: 12, color: GoQDColors.textSecondary)),
                      ),
                  ],
                ],
              ),
            ),
          const SizedBox(height: 20),
          const Text('点位说明',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          const Text(
            '卡片 ID 规则：{学校}-{区域}-{位置}-{序号}\n'
            'CT 食堂 · LB 图书馆 · DM 宿舍 · BB 公告栏\n'
            'CR 教室区 · CL 社团活动室 · SP 体育场馆 · GW 校门',
            style: TextStyle(fontSize: 13, height: 1.7, color: GoQDColors.textSecondary),
          ),
        ],
      ),
    );
  }

  static String _badgeText(int n) => n >= 5 ? '已解锁' : '$n/5';
}

class _StatBox extends StatelessWidget {
  const _StatBox({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Text(value,
              style: const TextStyle(
                  fontSize: 22, fontWeight: FontWeight.w700, color: GoQDColors.primary)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12, color: GoQDColors.textSecondary)),
        ],
      );
}
